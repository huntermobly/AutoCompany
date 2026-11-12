"""Start an isolated local server, run the full synthetic journey, then stop only that server."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import httpx

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from compliance.database import Database
from demo_flow import run

with tempfile.TemporaryDirectory(prefix="compliance-smoke-") as temp:
    temp=Path(temp)
    db_path=temp/"smoke.sqlite3"
    db=Database(db_path)
    identities={role:db.provision("synthetic-smoke-tenant",role) for role in ["owner","professional","content_reviewer"]}
    credentials=temp/"credentials.json"
    credentials.write_text(json.dumps(identities),encoding="utf-8")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1",0))
        port=sock.getsockname()[1]
    env={**os.environ,"COMPLIANCE_DB":str(db_path),"COMPLIANCE_MODE":"test","ENABLE_EXTERNAL_PROVIDERS":"false"}
    log=(ROOT/"docs"/"http-smoke-server.log").open("w",encoding="utf-8")
    proc=subprocess.Popen([sys.executable,"-m","compliance","serve","--port",str(port)],
                          cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,
                          creationflags=subprocess.CREATE_NO_WINDOW if os.name=="nt" else 0)
    try:
        started=False
        with httpx.Client(trust_env=False,timeout=1) as client:
            for attempt in range(100):
                if proc.poll() is not None:
                    raise RuntimeError("Server exited; see docs/http-smoke-server.log")
                try:
                    if client.get(f"http://127.0.0.1:{port}/health").status_code==200:
                        started=True
                        break
                except httpx.RequestError:
                    pass
                time.sleep(.1)
        if not started:
            raise RuntimeError("Local server did not start")
        run(f"http://127.0.0.1:{port}",credentials,ROOT/"docs")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
        log.close()
