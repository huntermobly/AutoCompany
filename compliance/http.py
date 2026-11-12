"""Small typed Starlette route registry and OpenAPI 3.1 generation."""
from dataclasses import dataclass
import json
import re
import sqlite3
from typing import Any
from pydantic import BaseModel, ValidationError
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route
from .auth import authenticate
from .database import require_role

@dataclass
class Context:
    db: Any
    principal: dict
    app: Any
    path: dict
    query: dict

class API:
    def __init__(self):
        self.definitions = []

    def route(self, method, path, model=None, roles=None, status=200, public=False):
        def register(handler):
            self.definitions.append(dict(method=method, path=path, model=model, roles=roles,
                                         status=status, public=public, handler=handler))
            return handler
        return register

    def routes(self):
        routes = []
        for definition in self.definitions:
            def factory(item):
                async def endpoint(request: Request):
                    try:
                        parsed = None
                        if item["model"]:
                            if request.headers.get("content-type", "").split(";")[0] != "application/json":
                                raise HTTPException(415, "Use application/json")
                            body = bytearray()
                            async for chunk in request.stream():
                                body.extend(chunk)
                                if len(body) > request.app.state.settings.max_body_bytes:
                                    raise HTTPException(413, "Request body too large")
                            try:
                                parsed = item["model"].model_validate_json(bytes(body))
                            except ValidationError as error:
                                return JSONResponse({"error": "validation_error", "details": error.errors(include_input=False, include_context=False, include_url=False)}, status_code=422)
                        def execute():
                            with request.app.state.database.transaction() as db:
                                identity = {} if item["public"] else authenticate(db, request.headers.get("authorization"))
                                if item["roles"]:
                                    require_role(identity, *item["roles"])
                                ctx = Context(db, identity, request.app, request.path_params, dict(request.query_params))
                                result = item["handler"](ctx, parsed)
                                return result
                        result = await run_in_threadpool(execute)
                        return result if isinstance(result, Response) else JSONResponse(result, status_code=item["status"])
                    except HTTPException as error:
                        return JSONResponse({"error": error.detail}, status_code=error.status_code, headers=error.headers)
                    except ValidationError as error:
                        return JSONResponse({"error": "validation_error", "details": error.errors(include_input=False, include_context=False, include_url=False)}, status_code=422)
                    except sqlite3.IntegrityError:
                        return JSONResponse({"error": "Conflicting or duplicate record"}, status_code=409)
                return endpoint
            routes.append(Route(definition["path"], factory(definition), methods=[definition["method"]]))
        return routes

    def openapi(self):
        paths, schemas = {}, {}
        for item in self.definitions:
            operation = {"operationId": item["handler"].__name__, "summary": (item["handler"].__doc__ or item["handler"].__name__).strip(),
                         "responses": {str(item["status"]): {"description": "Success"}, "401": {"description": "Authentication required"},
                                       "403": {"description": "Role not permitted"}, "404": {"description": "Not found"},
                                       "409": {"description": "State conflict"}, "422": {"description": "Validation failed"},
                                       "503": {"description": "Integration unavailable"}}}
            if not item["public"]:
                operation["security"] = [{"BearerAuth": []}]
            parameters = [{"name": name, "in": "path", "required": True, "schema": {"type": "string"}}
                          for name in re.findall(r"\{(\w+)\}", item["path"])]
            if item["method"] == "GET":
                parameters += [{"name": "as_of", "in": "query", "required": False, "schema": {"type": "string", "format": "date"}}]
            if parameters:
                operation["parameters"] = parameters
            if item["model"]:
                schema = item["model"].model_json_schema(ref_template="#/components/schemas/{model}")
                schemas.update(schema.pop("$defs", {}))
                schemas[item["model"].__name__] = schema
                operation["requestBody"] = {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/"+item["model"].__name__}}}}
            paths.setdefault(item["path"], {})[item["method"].lower()] = operation
        return {"openapi": "3.1.0", "info": {"title": "India Company Compliance Backend", "version": "0.1.0",
                "description": "Preparation and evidence API. No government submission. No frontend."},
                "paths": paths, "components": {"schemas": schemas, "securitySchemes": {"BearerAuth": {"type": "http", "scheme": "bearer"}}}}

api = API()
