import hashlib
from starlette.exceptions import HTTPException


def authenticate(db, header):
    parts = (header or "").split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(401, "Bearer token required", headers={"WWW-Authenticate": "Bearer"})
    hashed = hashlib.sha256(parts[1].encode()).hexdigest()
    row = db.execute("SELECT id,tenant_id,role FROM principals WHERE token_hash=? AND revoked=0", (hashed,)).fetchone()
    if not row:
        raise HTTPException(401, "Invalid or revoked token")
    return dict(row)

