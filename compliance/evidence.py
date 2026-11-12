import base64
import binascii
import io
import json
import zipfile
from starlette.exceptions import HTTPException
from .database import digest, get, insert

def upload(db, principal, company_id, body):
    get(db, "company", company_id, principal)
    try:
        content = base64.b64decode(body.content_base64, validate=True)
    except (ValueError, binascii.Error):
        raise HTTPException(422, "Invalid base64")
    if not content or len(content) > 5_000_000:
        raise HTTPException(413, "Evidence must contain 1 to 5,000,000 bytes")
    if body.media_type == "application/pdf" and not content.startswith(b"%PDF-"):
        raise HTTPException(422, "PDF header missing")
    if body.media_type in {"text/plain", "application/json"}:
        try:
            text = content.decode("utf-8")
            if body.media_type == "application/json":
                json.loads(text)
        except (ValueError, UnicodeError):
            raise HTTPException(422, "Evidence is not valid UTF-8 text/JSON")
    if body.media_type.endswith("wordprocessingml.document"):
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as z:
                if len(z.infolist()) > 200 or sum(i.file_size for i in z.infolist()) > 20_000_000:
                    raise ValueError("Oversized archive")
                if "word/document.xml" not in z.namelist():
                    raise ValueError("Not a DOCX")
                if any(".." in n.split("/") or n.startswith("/") or "vbaProject" in n for n in z.namelist()):
                    raise ValueError("Unsafe archive")
        except (ValueError, zipfile.BadZipFile):
            raise HTTPException(422, "Unsafe or invalid DOCX")
    data = body.model_dump(mode="json", exclude={"content_base64"})
    row = insert(db, "evidence", principal, {**data, "sha256": digest(content), "size": len(content),
                 "scan_status": "not_scanned", "legal_hold": False, "retain_until": None, "deleted": False}, company_id)
    db.execute("INSERT INTO blobs VALUES(?,?)", (row["id"], content))
    return row

def content(db, identity, principal):
    row = get(db, "evidence", identity, principal)
    blob = db.execute("SELECT content FROM blobs WHERE id=?", (identity,)).fetchone()
    if row.get("deleted") or not blob:
        raise HTTPException(410, "Evidence content has been deleted")
    if digest(blob[0]) != row["sha256"]:
        raise HTTPException(409, "Evidence integrity check failed")
    return row, bytes(blob[0])
