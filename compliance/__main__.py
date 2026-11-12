"""Local provisioning and server entry point. No public bootstrap route."""
import argparse
import json
from pathlib import Path
from uuid import uuid4
from .config import Settings
from .database import Database

def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    bootstrap = sub.add_parser("bootstrap")
    bootstrap.add_argument("--out", default=".local/credentials.json")
    serve = sub.add_parser("serve")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    settings = Settings.from_env()
    if args.command == "bootstrap":
        output = Path(args.out)
        if output.exists():
            parser.error("Credentials already exist; do not overwrite active tokens")
        db = Database(settings.db_path)
        tenant = str(uuid4())
        credentials = {role: db.provision(tenant, role) for role in
                       ["owner", "operator", "director", "professional", "content_reviewer"]}
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(credentials, indent=2), encoding="utf-8")
        print(f"Created local-only credentials in {output}. Keep this file private.")
    else:
        import uvicorn
        from .app import create_app
        uvicorn.run(create_app(settings), host=args.host, port=args.port)

if __name__ == "__main__":
    main()
