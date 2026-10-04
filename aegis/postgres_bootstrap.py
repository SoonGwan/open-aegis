"""Initialize an empty native workspace atomically, without a temporary SQLite DB."""
import secrets
from . import postgres_transfer as transfer
from .audit import GENESIS
from .migrations import SCHEMA_VERSION
from .postgres_maintenance import offline_export


def initialize(dsn,schema):
    transfer.validate_schema(schema)
    with transfer.connect(dsn) as db,db.transaction():
        # Fresh and existing names share the same runtime admission key. Refuse
        # active initialization, protected requests or an owner before any DDL.
        offline_export(db,schema)
        transfer.create_schema(db,schema)
        db.execute('INSERT INTO audit_state VALUES (1,%s,0,%s,0)',(secrets.token_hex(16),GENESIS))
        db.execute('INSERT INTO storage_metadata VALUES (1,%s,%s,0)',(transfer.FORMAT,SCHEMA_VERSION))
        metadata,audit=transfer.validate_postgres(db)
        manifest=transfer.postgres_manifest(db)
        if any(manifest[table]['rows']!=(1 if table=='audit_state' else 0) for table in transfer.TABLES):
            raise transfer.TransferError('새 워크스페이스 초기 검증에 실패했습니다.')
    return {'format':transfer.FORMAT,'schema':schema,'schema_version':SCHEMA_VERSION,
            'created':True,'users':0,'sessions':metadata['session_count'],'audit':audit,
            'manifest':manifest,'service_started':False}
