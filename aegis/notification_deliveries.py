"""Durable notification event cursor and single-attempt receiver receipts."""
import threading,time
from contextlib import nullcontext
from fastapi import HTTPException
from .remote_mcp import _digest
from .store_util import now
from .runtime import TaskControl
from .notification_transport import DispatchError
from .notification_channels import KIND

STATE='notification-source-v1'

class Deliveries:
    def __init__(self,store,channels):
        self.store=store;self.channels=channels;self.stop=threading.Event();self.gate=threading.Lock();self.thread=None
        self.errors=0;self.last_error_at=None

    def start(self):
        while self.recover():pass
        if not self.channels.webhooks.destinations:return
        thread=threading.Thread(target=self.watch,name='aegis-notifications',daemon=True);thread.start();self.thread=thread

    def close(self):
        self.stop.set()
        if self.thread:self.thread.join()

    def watch(self):
        while not self.stop.is_set():
            try:
                recovered=self.recover();scanned=self.scan();dispatched=self.dispatch_one()
                progress=recovered or scanned or dispatched
            except Exception:self.errors+=1;self.last_error_at=now();progress=False
            self.stop.wait(.02 if progress else .25)

    def _select(self,kind,state,db,*,limit=25):
        pg=getattr(self.store,'backend',None)=='postgres';marker='%s' if pg else '?'
        expr="data::jsonb->>'status'" if pg else "json_extract(data,'$.status')"
        rows=db.execute(f'SELECT id FROM records WHERE kind={marker} AND {expr}={marker} ORDER BY rowid LIMIT {limit}',(kind,state)).fetchall()
        return [self.store.get(kind,row['id'],connection=db) for row in rows]

    def scan(self):
        # One source event per transaction caps channel fanout at25. Cursor and receipts commit together.
        with self.store.read_transaction() as db:
            if not self._select(KIND,'active',db):return False
        with self.store.lock,self.store.write_transaction() as db:
            channels=self._select(KIND,'active',db)
            if not channels:return False
            saved=self.store.get('notification_state',STATE,connection=db)
            after=saved['after'] if saved else min(row.get('source_after',0) for row in channels)
            if type(after) is not int or after<0:raise ValueError('notification_cursor_invalid')
            after=max(after,min(row.get('source_after',0) for row in channels))
            if after>self.store.event_progress(after,connection=db)['latest_event_seq']:raise ValueError('notification_cursor_ahead')
            events=self.store.events(after=after,limit=1,connection=db)
            if not events:return False
            event=events[0];detail=event['detail'] if type(event['detail']) is dict else {};status=detail.get('task_status')
            if detail.get('notification_kind')=='task.terminal' and event['task_id'] and status in ('completed','failed','stopped','interrupted','rejected'):
                task=self.store.get('tasks',event['task_id'],connection=db)
                if task:
                    for channel in channels:
                        if event['seq']<=channel.get('source_after',0) or status not in channel['task_statuses']:continue
                        id=_digest(['aegis-notification-delivery-v1',channel['id'],event['seq']])[:32]
                        if self.store.get('notification_deliveries',id,connection=db):continue
                        record={'id':id,'channel_id':channel['id'],'channel_revision':channel['revision'],'destination_id':channel['destination_id'],
                                'destination_fingerprint':channel['destination_fingerprint'],'source_event_seq':event['seq'],'task_id':event['task_id'],
                                'status':'queued','attempts':0,'created_at':now(),'updated_at':now(),
                                'payload':{'format':'aegis-notification-v1','delivery_id':id,'kind':'task.'+status,'task_id':event['task_id'],
                                           'task_name':str(task.get('name',''))[:120],'occurred_at':event['ts']}}
                        self.store.put_many([('notification_deliveries',record)],connection=db)
                        self.store.event(None,'알림 전송을 준비했습니다.',detail={'delivery_id':id,'channel_id':channel['id'],'source_event_seq':event['seq']},connection=db)
            self.store.put_many([('notification_state',{'id':STATE,'after':event['seq']})],connection=db)
            return True

    def _finish(self,before,status,code,db,*,http_status=None):
        timestamp=now();record={**before,'status':status,'result_code':code,'http_status':http_status,'updated_at':timestamp}
        rows=[('notification_deliveries',record)]
        if before.get('attempts'):
            attempt_id=before['id']+':'+str(before['attempts'])
            attempt=self.store.get('notification_attempts',attempt_id,connection=db)
            if attempt:rows.append(('notification_attempts',{**attempt,'status':status,'result_code':code,'http_status':http_status,'finished_at':timestamp}))
        self.store.put_many(rows,connection=db)
        self.store.event(None,'알림 전송 상태를 기록했습니다.',detail={'delivery_id':before['id'],'status':status,'result_code':code,'http_status':http_status},connection=db)
        return record

    def recover(self):
        if not self.gate.acquire(blocking=False):return False
        try:
            with self.store.read_transaction() as db:
                if not self._select('notification_deliveries','dispatching',db):return False
            with self.store.lock,self.store.write_transaction() as db:
                records=self._select('notification_deliveries','dispatching',db)
                for record in records:self._finish(record,'unknown','process_receipt_unconfirmed',db)
                return bool(records)
        finally:self.gate.release()

    def _review(self,record,db):
        channel=self.channels.get(record['channel_id'],db)
        actor=record.get('test_approved_by') if record.get('test_mode') else channel.get('approved_by')
        if not actor:raise DispatchError('channel_not_approved')
        try:self.channels.actor(actor,db)
        except HTTPException:raise DispatchError('channel_approver_unavailable') from None
        if (not record.get('test_mode') and not channel['enabled']) or channel['revision']!=record['channel_revision']:raise DispatchError('channel_changed')
        prepared=self.channels.webhooks.prepare(record['destination_id'])
        if prepared.fingerprint!=record['destination_fingerprint']:raise DispatchError('destination_changed')
        return channel,prepared

    def _due(self,db):
        pg=getattr(self.store,'backend',None)=='postgres';marker='%s' if pg else '?'
        field=lambda alias,key:f"{alias}.data::jsonb->>'{key}'" if pg else f"json_extract({alias}.data,'$.{key}')"
        timestamp=f"({field('runtime','next_at')})::numeric" if pg else field('runtime','next_at')
        rows=db.execute(f"SELECT delivery.id FROM records delivery LEFT JOIN records runtime ON runtime.kind='notification_runtime' AND runtime.id={field('delivery','channel_id')} WHERE delivery.kind={marker} AND {field('delivery','status')}='queued' AND coalesce({timestamp},0)<={marker} ORDER BY delivery.rowid LIMIT 1",('notification_deliveries',now())).fetchall()
        return [self.store.get('notification_deliveries',row['id'],connection=db) for row in rows]

    def dispatch_one(self):
        if not self.gate.acquire(blocking=False):return False
        try:
            selected=None;prepared=None
            with self.store.read_transaction() as db:
                if not self._due(db):return False
            with self.store.lock,self.store.write_transaction() as db:
                # Apply persisted per-channel rate before network I/O. No in-memory-only cooldown.
                for record in self._due(db):
                    try:channel,prepared=self._review(record,db)
                    except (DispatchError,HTTPException) as error:
                        code=error.code if isinstance(error,DispatchError) else 'channel_unavailable'
                        self._finish(record,'blocked',code,db);return True
                    timestamp=now();selected={**record,'status':'dispatching','attempts':record['attempts']+1,'updated_at':timestamp}
                    attempt={'id':record['id']+':'+str(selected['attempts']),'delivery_id':record['id'],'status':'dispatching','attempt':selected['attempts'],'started_at':timestamp}
                    self.store.put_many([('notification_deliveries',selected),('notification_attempts',attempt),
                                         ('notification_runtime',{'id':channel['id'],'next_at':timestamp+channel['interval_seconds']})],connection=db)
                    self.store.event(None,'알림 전송 시도를 기록했습니다.',detail={'delivery_id':record['id'],'attempt':selected['attempts']},connection=db)
                    break
            if selected is None:return False
            status='unknown';code='transport_unconfirmed';http_status=None
            try:
                with getattr(self.store,'execution_permit',nullcontext)():
                    receipt=self.channels.webhooks.send(prepared,selected['payload'],selected['id'],control=TaskControl(self.stop,deadline=time.monotonic()+8))
                status='delivered';code='receiver_accepted';http_status=receipt['http_status']
            except DispatchError as error:
                status='failed' if error.status is not None or not error.possibly_sent else 'unknown';code=error.code;http_status=error.status
            with self.store.lock,self.store.write_transaction() as db:
                current=self.store.get('notification_deliveries',selected['id'],connection=db)
                if current is None or current['status']!='dispatching' or current['attempts']!=selected['attempts']:raise ValueError('notification_attempt_changed')
                self._finish(current,status,code,db,http_status=http_status)
            return True
        finally:self.gate.release()

    def retry(self,id,*,expected_attempts,request_id,confirm_possible_duplicate,actor):
        if type(expected_attempts) is not int or not 0<=expected_attempts<=3:raise HTTPException(422,'현재 전송 시도 횟수를 확인하세요.')
        if type(confirm_possible_duplicate) is not bool or not isinstance(request_id,str) or not 16<=len(request_id)<=64:raise HTTPException(422,'재전송 요청을 확인하세요.')
        operation_id=_digest(['aegis-notification-retry-v1',id,actor['id'],request_id])[:32]
        requested=_digest({'expected_attempts':expected_attempts,'confirm_possible_duplicate':confirm_possible_duplicate})
        with self.store.lock,self.store.write_transaction() as db:
            actor=self.channels.actor(actor,db)
            previous=self.store.get('notification_retry_operations',operation_id,connection=db)
            if previous:
                if previous['request_sha256']!=requested:raise HTTPException(409,'같은 재전송 요청의 내용이 다릅니다.')
                return {**previous['result'],'replayed':True}
            record=self.store.get('notification_deliveries',id,connection=db)
            if record is None:raise HTTPException(404,'알림 전송 기록이 없습니다.')
            if record['status'] not in ('failed','unknown','blocked') or record['attempts']!=expected_attempts:raise HTTPException(409,'알림 전송 상태가 변경되었습니다.')
            if expected_attempts>=3:raise HTTPException(409,'알림 전송은 최대3회입니다.')
            if (record['status']=='unknown' or record.get('http_status') is not None) and not confirm_possible_duplicate:raise HTTPException(409,'수신처가 이미 처리했을 가능성을 확인한 뒤 재전송하세요.')
            try:self._review(record,db)
            except (DispatchError,HTTPException):raise HTTPException(409,'원래 승인한 수신처와 현재 채널·관리자 설정을 확인하세요.') from None
            updated={**record,'status':'queued','updated_at':now(),'retry_requested_by':actor}
            result={'delivery_id':id,'status':'queued','previous_attempts':expected_attempts,'replayed':False}
            self.store.put_many([('notification_deliveries',updated),('notification_retry_operations',{'id':operation_id,'request_sha256':requested,'result':result,'actor':actor,'created_at':now()})],connection=db)
            self.store.event(None,'관리자가 알림 재전송을 요청했습니다.',detail={'delivery_id':id,'previous_attempts':expected_attempts,'confirm_possible_duplicate':confirm_possible_duplicate,'actor':actor},connection=db)
            return result

    def test(self,id,data,actor):
        delivery_id=_digest(['aegis-notification-test-v1',id,actor['id'],data.request_id])[:32]
        requested=_digest({'expected_revision':data.expected_revision})
        with self.store.lock,self.store.write_transaction() as db:
            actor=self.channels.actor(actor,db)
            previous=self.store.get('notification_deliveries',delivery_id,connection=db)
            if previous:
                if previous['test_request_sha256']!=requested:raise HTTPException(409,'같은 알림 테스트 요청의 내용이 다릅니다.')
                return {'delivery_id':delivery_id,'replayed':True}
            channel=self.channels.get(id,db)
            if channel['revision']!=data.expected_revision:raise HTTPException(409,'알림 채널 버전이 변경되었습니다.')
            try:prepared=self.channels.webhooks.prepare(channel['destination_id'])
            except DispatchError:raise HTTPException(409,'테스트할 수신처 설정을 확인하세요.') from None
            timestamp=now()
            record={'id':delivery_id,'channel_id':id,'channel_revision':channel['revision'],'destination_id':channel['destination_id'],
                    'destination_fingerprint':prepared.fingerprint,'source_event_seq':None,'task_id':None,
                    'test_mode':True,'test_approved_by':actor,'test_request_sha256':requested,
                    'status':'queued','attempts':0,'created_at':timestamp,'updated_at':timestamp,
                    'payload':{'format':'aegis-notification-v1','delivery_id':delivery_id,'kind':'test','occurred_at':timestamp}}
            self.store.put_many([('notification_deliveries',record)],connection=db)
            self.store.event(None,'관리자가 알림 테스트를 요청했습니다.',detail={'delivery_id':delivery_id,'channel_id':id,'revision':channel['revision'],'actor':actor},connection=db)
            return {'delivery_id':delivery_id,'replayed':False}
