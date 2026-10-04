"""Cooperative PostgreSQL ownership and transaction/request fencing."""
from . import postgres_transfer as transfer
from .maintenance import WorkspaceBusy
from .migrations import SCHEMA_VERSION


def runtime_key(db,schema):
    return db.execute("SELECT hashtextextended('open-aegis-runtime:'||current_database()||':'||%s,0) AS key",(schema,)).fetchone()['key']


def offline_write(db,schema):
    # Unbound writers must not overlap a runtime owner or protected request.
    db.execute('SELECT pg_advisory_xact_lock(%s)',(runtime_key(db,schema),))


def offline_export(db,schema):
    if not db.execute('SELECT pg_try_advisory_xact_lock(%s) AS acquired',(runtime_key(db,schema),)).fetchone()['acquired']:
        raise WorkspaceBusy('PostgreSQL 워크스페이스가 사용 중입니다. 서버를 종료한 뒤 전송하세요.')


class PostgresLease:
    def __init__(self,dsn,schema):
        transfer.validate_schema(schema)
        self._dsn=dsn;self.schema=schema;self.closed=False
        self.connection=transfer.connect(dsn)
        try:
            self.key=runtime_key(self.connection,schema)
            acquired=self.connection.execute('SELECT pg_try_advisory_lock(%s) AS acquired',(self.key,)).fetchone()['acquired']
            if not acquired:raise WorkspaceBusy('PostgreSQL 워크스페이스를 다른 서버 또는 작업이 사용 중입니다.')
            with self.connection.transaction():
                transfer.set_schema(self.connection,schema)
                metadata=self.connection.execute('SELECT * FROM storage_metadata WHERE id=1').fetchone()
                if not metadata or metadata['format']!=transfer.FORMAT or metadata['sqlite_schema']!=SCHEMA_VERSION:
                    raise transfer.TransferError('지원하지 않는 PostgreSQL 저장 형식입니다.')
                identity=self.connection.execute('SELECT pid,backend_start FROM pg_stat_activity WHERE pid=pg_backend_pid()').fetchone()
                self.pid=identity['pid'];self.backend_start=identity['backend_start']
            # Hold shared ownership before dropping exclusive admission: no gap.
            self.connection.execute('SELECT pg_advisory_lock_shared(%s)',(self.key,))
            self.connection.execute('SELECT pg_advisory_unlock(%s)',(self.key,))
        except BaseException:
            self.close()
            raise

    def protect(self,db,dsn,schema):
        if self.closed or self.connection.closed or dsn!=self._dsn or schema!=self.schema:
            raise WorkspaceBusy('PostgreSQL 실행 소유권을 확인할 수 없습니다. 서버를 다시 시작하세요.')
        if runtime_key(db,schema)!=self.key:
            raise WorkspaceBusy('PostgreSQL 실행 연결이 소유한 DB와 다릅니다.')
        db.execute('SELECT pg_advisory_xact_lock_shared(%s)',(self.key,))
        # Dedicated owner PID + backend start prevent an old process accepting a
        # replacement owner. The xact gate prevents takeover until work finishes.
        valid=db.execute("""SELECT 1 FROM pg_locks l JOIN pg_stat_activity a ON a.pid=l.pid
          WHERE l.locktype='advisory' AND l.database=(SELECT oid FROM pg_database WHERE datname=current_database())
            AND l.classid=%s::oid AND l.objid=%s::oid AND l.objsubid=1
            AND l.mode='ShareLock' AND l.granted AND l.pid=%s AND a.backend_start=%s""",
          ((self.key>>32)&0xffffffff,self.key&0xffffffff,self.pid,self.backend_start)).fetchone()
        if not valid:raise WorkspaceBusy('PostgreSQL 실행 소유권을 잃었습니다. 새 작업을 실행하지 않습니다.')

    def close(self):
        if not self.closed:
            self.closed=True
            self.connection.close()  # Session locks release; never reconnect/reacquire.

    def __enter__(self):return self
    def __exit__(self,*args):self.close()
