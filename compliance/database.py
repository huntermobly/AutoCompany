"""SQLite repository with transactions, immutable records and hashed access tokens."""
import hashlib
import json
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from starlette.exceptions import HTTPException


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(value):
    raw = value if isinstance(value, bytes) else json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


class Database:
    def __init__(self, path):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self.transaction() as db:
            db.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS principals (
                id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, role TEXT NOT NULL,
                token_hash TEXT UNIQUE NOT NULL, revoked INTEGER NOT NULL DEFAULT 0);
            CREATE TABLE IF NOT EXISTS grants (
                principal_id TEXT NOT NULL, company_id TEXT NOT NULL,
                PRIMARY KEY(principal_id, company_id));
            CREATE TABLE IF NOT EXISTS records (
                id TEXT PRIMARY KEY, kind TEXT NOT NULL, tenant_id TEXT NOT NULL,
                company_id TEXT, payload TEXT NOT NULL, created_at TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS records_scope ON records(tenant_id,company_id,kind);
            CREATE TABLE IF NOT EXISTS blobs (id TEXT PRIMARY KEY, content BLOB NOT NULL);
            CREATE TABLE IF NOT EXISTS audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT, tenant_id TEXT NOT NULL,
                company_id TEXT, actor_id TEXT NOT NULL, action TEXT NOT NULL,
                target_id TEXT NOT NULL, occurred_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY);
            INSERT OR IGNORE INTO schema_migrations VALUES (1);
            """)

    @contextmanager
    def transaction(self):
        db = sqlite3.connect(self.path, timeout=20)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("BEGIN IMMEDIATE")
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def provision(self, tenant_id, role, principal_id=None):
        token = secrets.token_urlsafe(40)
        identity = principal_id or str(uuid4())
        with self.transaction() as db:
            db.execute("INSERT INTO principals(id,tenant_id,role,token_hash) VALUES(?,?,?,?)",
                       (identity, tenant_id, role, hashlib.sha256(token.encode()).hexdigest()))
        return {"id": identity, "tenant_id": tenant_id, "role": role, "token": token}


def insert(db, kind, principal, payload, company_id=None, record_id=None):
    identity = record_id or str(uuid4())
    row = {"id": identity, "kind": kind, "tenant_id": principal["tenant_id"],
           "company_id": company_id, "created_at": now(), **payload}
    db.execute("INSERT INTO records VALUES(?,?,?,?,?,?)",
               (identity, kind, principal["tenant_id"], company_id, json.dumps(row), row["created_at"]))
    audit(db, principal, kind + ".created", identity, company_id)
    return row


def update(db, row, changes):
    row = {**row, **changes}
    db.execute("UPDATE records SET payload=? WHERE id=?", (json.dumps(row), row["id"]))
    return row


def get(db, kind, identity, principal):
    row = db.execute("SELECT payload FROM records WHERE id=? AND kind=? AND tenant_id=?",
                     (identity, kind, principal["tenant_id"])).fetchone()
    if not row:
        raise HTTPException(404, "Record not found")
    result = json.loads(row[0])
    company_id = result["company_id"] or (result["id"] if kind == "company" else None)
    if company_id:
        authorize_company(db, principal, company_id)
    return result


def all_records(db, kind, principal, company_id=None):
    if company_id:
        authorize_company(db, principal, company_id)
    # Commit/insertion order remains stable even when the system clock repeats or moves back.
    rows = db.execute("SELECT payload FROM records WHERE kind=? AND tenant_id=? ORDER BY rowid",
                      (kind, principal["tenant_id"])).fetchall()
    out = [json.loads(r[0]) for r in rows]
    if company_id:
        return [r for r in out if r["company_id"] == company_id]
    if principal["role"] != "owner":
        granted = {r[0] for r in db.execute("SELECT company_id FROM grants WHERE principal_id=?", (principal["id"],))}
        out = [r for r in out if (r["id"] if kind == "company" else r["company_id"]) in granted or (kind != "company" and r["company_id"] is None)]
    return out


def authorize_company(db, principal, company_id):
    company = db.execute("SELECT 1 FROM records WHERE id=? AND kind='company' AND tenant_id=?",
                         (company_id, principal["tenant_id"])).fetchone()
    grant = principal["role"] == "owner" or db.execute(
        "SELECT 1 FROM grants WHERE principal_id=? AND company_id=?", (principal["id"], company_id)).fetchone()
    if not company or not grant:
        raise HTTPException(404, "Company not found")


def require_role(principal, *roles):
    if principal["role"] not in roles:
        raise HTTPException(403, "Role not permitted")


def audit(db, principal, action, target_id, company_id=None):
    db.execute("INSERT INTO audit(tenant_id,company_id,actor_id,action,target_id,occurred_at) VALUES(?,?,?,?,?,?)",
               (principal["tenant_id"], company_id, principal["id"], action, target_id, now()))

