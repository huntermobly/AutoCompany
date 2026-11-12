from collections import defaultdict, deque
from contextlib import asynccontextmanager
import hashlib
import json
import time
import httpx
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from .config import Settings
from .database import Database
from .http import api
from .providers import AIProvider, SandboxProvider
from .routes import companies, legal, workflows  # register routes

class SecurityMiddleware:
    def __init__(self, app):
        self.app = app
        self.windows = defaultdict(deque)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = dict(scope["headers"])
        key = hashlib.sha256(headers.get(b"authorization", b"anonymous")).hexdigest()
        stamp = time.monotonic()
        hits = self.windows[key]
        while hits and stamp - hits[0] >= 60:
            hits.popleft()
        if len(hits) >= 600:
            return await JSONResponse({"error": "Local rate limit reached"}, status_code=429,
                                      headers={"Retry-After": "60"})(scope, receive, send)
        hits.append(stamp)
        if len(self.windows) > 10000:
            self.windows = defaultdict(deque, {k: v for k, v in self.windows.items() if v and stamp-v[-1] < 60})
        async def secure(message):
            if message["type"] == "http.response.start":
                message.setdefault("headers", []).extend([(b"x-content-type-options", b"nosniff"),
                                                          (b"cache-control", b"no-store"),
                                                          (b"x-frame-options", b"DENY")])
            await send(message)
        await self.app(scope, receive, secure)

def create_app(settings=None, sandbox_transport=None, ai_transport=None, source_transport=None):
    settings = settings or Settings.from_env()
    database = Database(settings.db_path)
    if settings.mode == "production":
        with database.transaction() as db:
            for row in db.execute("SELECT payload FROM records WHERE kind IN ('rule', 'template', 'source_snapshot')"):
                payload = json.loads(row["payload"])
                if payload.get("synthetic") and payload.get("status") in {"approved", "verified"}:
                    raise ValueError("Production requires a clean database without active synthetic releases")
    sandbox = SandboxProvider(settings, sandbox_transport)
    ai = AIProvider(settings, ai_transport)
    source_client = httpx.Client(transport=source_transport, timeout=10, follow_redirects=False, trust_env=False)
    @asynccontextmanager
    async def lifespan(app):
        yield
        sandbox.close()
        ai.close()
        source_client.close()
    async def health(request):
        return JSONResponse({"status": "ok", "version": "0.1.0", "mode": settings.mode,
                             "government_submission": False, "frontend": False})
    async def openapi(request):
        return JSONResponse(api.openapi())
    app = Starlette(routes=[Route("/health", health), Route("/openapi.json", openapi)] + api.routes(), lifespan=lifespan)
    app.add_middleware(SecurityMiddleware)
    app.state.settings = settings
    app.state.database = database
    app.state.sandbox = sandbox
    app.state.ai = ai
    app.state.source_client = source_client
    return app
