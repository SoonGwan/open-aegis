"""Online native logical backup and atomic fresh-schema restore of reviewed data.

Archives contain data only, never SQL. Source sessions stay valid; restored sessions
are empty. Existing schemas are never replaced. Files include password hashes.
"""
import hashlib
import itertools
import json
import math
import os
from decimal import Decimal
from pathlib import Path
import tempfile
import zipfile
from . import postgres_transfer as transfer
from .audit import verify_chain,AuditIntegrityError
from .migrations import SCHEMA_VERSION

FORMAT='aegis-postgres-backup-v1'
MAX_ROW_BYTES=4*1024*1024
MAX_METADATA_BYTES=64*1024
MEMBERS={'metadata.json',*(table+'.ndjson' for table in transfer.TABLES)}


class BackupError(ValueError):pass


def encoded(values):
    return json.dumps(values,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()+b'\n'


def sequence(db,table,column):
    _,sql,_=transfer.driver()
    row=db.execute('SELECT n.nspname,c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE c.oid=pg_get_serial_sequence(%s,%s)::regclass',(table,column)).fetchone()
    if not row:raise BackupError('순번 할당기가 없습니다.')
    allocated=db.execute(sql.SQL('SELECT last_value,is_called FROM {}').format(sql.Identifier(row['nspname'],row['relname']))).fetchone()
    return allocated['last_value'] if allocated['is_called'] else 0


def layout(db,schema):
    rows=db.execute("SELECT c.relname,c.relkind FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname=%s AND c.relkind IN ('r','v','m','f','p')",(schema,)).fetchall()
    if {r['relname'] for r in rows}!=set(transfer.TABLES)|{'sessions','storage_metadata'} or any(r['relkind']!='r' for r in rows):
        raise BackupError('지원하는 백업 테이블 구성이 아닙니다.')


def backup(dsn,schema,output):
    transfer.validate_schema(schema);output=Path(output).absolute()
    output.parent.mkdir(parents=True,exist_ok=True)
    if output.exists() or output.is_symlink():raise BackupError('출력 경로가 이미 존재합니다.')
    fd,name=tempfile.mkstemp(prefix='.pg-backup-',dir=output.parent);os.close(fd);stage=Path(name)
    try:
        with transfer.connect(dsn) as db,db.transaction():
            db.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
            transfer.set_schema(db,schema);layout(db,schema)
            state,audit=transfer.validate_postgres(db,require_empty_sessions=False)
            manifest={}
            with zipfile.ZipFile(stage,'w',compression=zipfile.ZIP_STORED,allowZip64=True) as archive:
                for table,columns in transfer.TABLES.items():
                    digest=hashlib.sha256();count=0
                    with db.cursor(name='backup_'+table) as cursor,archive.open(table+'.ndjson','w',force_zip64=True) as target:
                        cursor.itersize=32
                        cursor.execute('SELECT '+','.join(columns)+' FROM '+table+' ORDER BY '+('id COLLATE "C"' if table=='users' else transfer.ORDER[table]))
                        for row in cursor:
                            data=encoded([row[key] for key in columns])
                            if len(data)>MAX_ROW_BYTES:raise BackupError('백업 레코드가 4MiB 한도를 초과했습니다.')
                            target.write(data);digest.update(data);count+=1
                    manifest[table]={'rows':count,'sha256':digest.hexdigest()}
                metadata={'format':FORMAT,'storage_format':transfer.FORMAT,'schema_version':SCHEMA_VERSION,
                          'source_schema':schema,'manifest':manifest,'audit':audit,
                          'record_sequence':sequence(db,'records','rowid'),'event_sequence':state['event_sequence'],
                          'omitted_sessions':state['session_count']}
                archive.writestr('metadata.json',encoded(metadata))
        # Validate the closed archive, then publish without overwriting a concurrent creator.
        validate(stage)
        with stage.open('rb') as file:os.fsync(file.fileno())
        os.link(stage,output)
        directory=os.open(output.parent,os.O_RDONLY)
        try:os.fsync(directory)
        finally:os.close(directory)
        return {**metadata,'output':str(output),'source_sessions_preserved':True}
    finally:stage.unlink(missing_ok=True)


class Rows:
    def __init__(self,iterator):self.iterator=iter(iterator)
    def __iter__(self):return self.iterator
    def fetchone(self):return next(self.iterator,None)


class Archive:
    def __init__(self,source):
        self.file=zipfile.ZipFile(source,'r')
        try:
            entries=self.file.infolist()
            if len(entries)!=len(MEMBERS) or {i.filename for i in entries}!=MEMBERS or any(i.compress_type!=zipfile.ZIP_STORED or i.flag_bits&1 for i in entries):
                raise BackupError('백업 파일 구성이 올바르지 않습니다.')
            with self.file.open('metadata.json') as file:raw=file.read(MAX_METADATA_BYTES+1)
            if len(raw)>MAX_METADATA_BYTES:raise BackupError('백업 메타데이터 크기를 초과했습니다.')
            self.metadata=json.loads(raw,object_pairs_hook=unique,parse_constant=invalid)
            m=self.metadata
            if not isinstance(m,dict) or m.get('format')!=FORMAT or m.get('storage_format')!=transfer.FORMAT or m.get('schema_version')!=SCHEMA_VERSION:
                raise BackupError('지원하지 않는 백업 형식입니다.')
            transfer.validate_schema(m.get('source_schema'))
            for key in ('record_sequence','event_sequence','omitted_sessions'):
                if type(m.get(key)) is not int or not 0<=m[key]<=9_223_372_036_854_775_807:raise BackupError('백업 순번/세션 기준이 올바르지 않습니다.')
            if not isinstance(m.get('manifest'),dict) or set(m['manifest'])!=set(transfer.TABLES):raise BackupError('백업 행 목록이 올바르지 않습니다.')
        except BaseException:self.close();raise

    def close(self):self.file.close()
    def __enter__(self):return self
    def __exit__(self,*args):self.close()

    def rows(self,table):
        columns=transfer.TABLES[table]
        with self.file.open(table+'.ndjson') as file:
            while True:
                raw=file.readline(MAX_ROW_BYTES+1)
                if not raw:break
                if len(raw)>MAX_ROW_BYTES or not raw.endswith(b'\n'):raise BackupError('백업 레코드 크기 또는 구분이 올바르지 않습니다.')
                values=json.loads(raw,object_pairs_hook=unique,parse_constant=invalid)
                if not isinstance(values,list) or len(values)!=len(columns):raise BackupError('백업 레코드 형식이 올바르지 않습니다.')
                validate_row(table,dict(zip(columns,values)))
                if encoded(values)!=raw:raise BackupError('백업 레코드 인코딩이 올바르지 않습니다.')
                yield dict(zip(columns,values))

    def hashes(self,table):
        digest=hashlib.sha256();count=0
        with self.file.open(table+'.ndjson') as file:
            while raw:=file.readline(MAX_ROW_BYTES+1):
                if len(raw)>MAX_ROW_BYTES or not raw.endswith(b'\n'):raise BackupError('백업 레코드 크기 또는 구분이 올바르지 않습니다.')
                digest.update(raw);count+=1
        return {'rows':count,'sha256':digest.hexdigest()}

    def execute(self,query):
        # Only the shared verifier's reviewed read operations are supported.
        if query=='SELECT * FROM audit_state WHERE id=1':
            rows=list(itertools.islice(self.rows('audit_state'),3))
            if len(rows)!=1 or rows[0].get('id')!=1:raise BackupError('감사 기준 기록이 올바르지 않습니다.')
            return Rows(rows)
        if query.startswith('SELECT e.*,h.previous_hash'):
            return Rows(self.events())
        if query.startswith('SELECT 1 FROM event_hashes h LEFT JOIN events'):
            return Rows(()) # events() checked the complete merge, including orphan links.
        raise BackupError('지원하지 않는 감사 읽기입니다.')

    def events(self):
        hashes=iter(self.rows('event_hashes'));link=next(hashes,None);previous=0
        for event in self.rows('events'):
            seq=event.get('seq')
            if type(seq) is not int or seq<=previous:raise BackupError('감사 순번 정렬이 올바르지 않습니다.')
            previous=seq
            if link is not None and link['seq']<seq:raise AuditIntegrityError('원본이 없는 감사 연결이 있습니다.')
            if link is None or link['seq']!=seq:raise AuditIntegrityError('감사 연결이 누락됐습니다.')
            yield {**event,'previous_hash':link['previous_hash'],'event_hash':link['event_hash']}
            link=next(hashes,None)
        if link is not None:raise AuditIntegrityError('원본이 없는 감사 연결이 있습니다.')


def unique(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise BackupError('중복 JSON 키가 있습니다.')
        result[key]=value
    return result


def invalid(_):raise BackupError('유한한 JSON 값이 필요합니다.')


def validate_row(table,row):
    integers={'records':{'rowid'},'users':{'disabled'},'events':{'seq'},
              'event_hashes':{'seq'},'audit_state':{'id','last_seq','sealed_legacy_until'}}[table]
    floats={'users':{'created_at','updated_at'},'events':{'ts'}}.get(table,set())
    nullable={'task_id','level','message','detail'} if table=='events' else set()
    for key,value in row.items():
        if key in integers:
            if type(value) is not int or not 0<=value<=9_223_372_036_854_775_807:raise BackupError('백업 정수 형식이 올바르지 않습니다.')
            if key in ('rowid','seq','id') and value==0:raise BackupError('백업 순번은 양수여야 합니다.')
            if key=='disabled' and value>2_147_483_647:raise BackupError('백업 사용자 상태가 올바르지 않습니다.')
        elif key in floats:
            if type(value) is not float or not math.isfinite(value):raise BackupError('백업 시각 형식이 올바르지 않습니다.')
        elif not isinstance(value,str) and not (key in nullable and value is None):
            raise BackupError('백업 텍스트 형식이 올바르지 않습니다.')
        elif isinstance(value,str) and '\0' in value:raise BackupError('백업 텍스트에 NUL이 있습니다.')
    if table=='users' and row['role'] not in ('admin','operator','viewer'):raise BackupError('백업 사용자 역할이 올바르지 않습니다.')


def verify(archive,checkpoint=None):
    metadata=archive.metadata
    for table in transfer.TABLES:
        if archive.hashes(table)!=metadata['manifest'][table]:raise BackupError('백업 행 해시가 일치하지 않습니다.')
        last=None
        for row in archive.rows(table):
            key=row[transfer.ORDER[table]]
            if last is not None and key<=last:raise BackupError('백업 행 순서가 올바르지 않습니다.')
            last=key
            if table=='records':
                json.loads(row['data'],parse_float=Decimal,parse_constant=invalid)
        if table=='records' and last is not None and last>metadata['record_sequence']:raise BackupError('자산 순번 기준이 올바르지 않습니다.')
        if table in ('events','event_hashes') and last is not None and last>metadata['event_sequence']:raise BackupError('감사 순번 기준이 올바르지 않습니다.')
    audit=verify_chain(archive,checkpoint)
    if audit!=metadata.get('audit'):raise BackupError('백업 감사 기준이 일치하지 않습니다.')
    return metadata


def validate(source,checkpoint=None):
    try:
        with Archive(source) as archive:return verify(archive,checkpoint)
    except (zipfile.BadZipFile,KeyError,TypeError,UnicodeError,RecursionError) as exc:
        raise BackupError('백업 파일을 읽을 수 없습니다.') from exc


def restore(source,dsn,schema,checkpoint=None):
    try:return _restore(source,dsn,schema,checkpoint)
    except (zipfile.BadZipFile,KeyError,TypeError,UnicodeError,RecursionError) as exc:
        raise BackupError('백업 파일을 읽을 수 없습니다.') from exc


def _restore(source,dsn,schema,checkpoint=None):
    transfer.validate_schema(schema)
    with Archive(source) as archive:
        metadata=verify(archive,checkpoint)
        with transfer.connect(dsn) as db,db.transaction():
            from .postgres_maintenance import offline_export
            offline_export(db,schema)
            qualified=transfer.create_schema(db,schema)
            for table,columns in transfer.TABLES.items():
                with db.cursor() as cursor,cursor.copy(f'COPY {qualified}.{table} ({",".join(columns)}) FROM STDIN') as copy:
                    for row in archive.rows(table):copy.write_row(tuple(row[k] for k in columns))
            db.execute('INSERT INTO storage_metadata VALUES (1,%s,%s,%s)',(transfer.FORMAT,SCHEMA_VERSION,metadata['event_sequence']))
            for table,column,maximum in [('records','rowid',metadata['record_sequence']),('events','seq',metadata['event_sequence'])]:
                db.execute('SELECT setval(pg_get_serial_sequence(%s,%s),%s,%s)',(qualified+'.'+table,column,max(1,maximum),maximum>0))
            _,audit=transfer.validate_postgres(db)
            if audit!=metadata['audit']:raise BackupError('복구된 감사 기록이 일치하지 않습니다.')
            # Round-trip typed native values back into archive canonical rows.
            for table,columns in transfer.TABLES.items():
                digest=hashlib.sha256();count=0
                with db.cursor(name='restore_verify_'+table) as cursor:
                    cursor.itersize=32;cursor.execute('SELECT '+','.join(columns)+' FROM '+table+' ORDER BY '+('id COLLATE "C"' if table=='users' else transfer.ORDER[table]))
                    for row in cursor:digest.update(encoded([row[k] for k in columns]));count+=1
                if {'rows':count,'sha256':digest.hexdigest()}!=metadata['manifest'][table]:raise BackupError('복구된 행 해시가 일치하지 않습니다.')
    return {**metadata,'schema':schema,'sessions_revoked':True,'existing_schema_preserved':True}
