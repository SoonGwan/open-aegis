"""Compare report generation with asynchronous dispatch on one owned SQLite fixture.

Development probe: requires test dependencies. No HTTP/network or real workspace.
The async measurement excludes ASGI sends, clients and concurrent execution.
"""
import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from aegis import reporting
from aegis.store import Store
from scripts.review_resource_load import bounded_int
from tests.test_report_streams import seed


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--records',type=bounded_int(1,6000),default=6000)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    result={'valid':False,'backend':'sqlite','fixture_records_per_kind':args.records}
    with tempfile.TemporaryDirectory(prefix='aegis-report-dispatch-') as folder:
        store=Store(Path(folder)/'fixture.db');seed(store,args.records)
        def measurement():return {'chunks':0,'bytes':0,'hash':hashlib.sha256()}
        def record(state,chunk):
            state['chunks']+=1;state['bytes']+=len(chunk);state['hash'].update(chunk)
        with patch.object(reporting,'now',return_value=1):
            direct=measurement();begin=time.monotonic()
            for chunk in reporting.report_chunks(store.path,'json','report-task'):record(direct,chunk)
            direct['seconds']=time.monotonic()-begin
            async def consume():
                dispatched=measurement();begin=time.monotonic()
                stream=reporting.report_stream(store.path,'json','report-task')
                try:
                    async for chunk in stream:record(dispatched,chunk)
                finally:await stream.aclose()
                dispatched['seconds']=time.monotonic()-begin
                return dispatched
            dispatched=asyncio.run(consume())
        for state in (direct,dispatched):state['sha256']=state.pop('hash').hexdigest()
        assert all(direct[key]==dispatched[key] for key in ('chunks','bytes','sha256'))
        result.update(valid=True,direct=direct,async_dispatch=dispatched,
            limitation='Same synthetic SQLite fixture; excludes HTTP, ASGI send and concurrency.')
    result['temporary_resources_removed']=True
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2))
    print(json.dumps(result))


if __name__=='__main__':main()
