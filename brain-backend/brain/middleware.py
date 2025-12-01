# Copyright (C) 2021 - 2025, Shanghai Yunsilicon Technology Co., Ltd.
# All rights reserved.

import logging
import time
import uuid
from contextvars import ContextVar

from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from brain.auth import verify_token

LOG = logging.getLogger(__name__)


request_id_var = ContextVar("request_id", default=None)


def set_request_id(req_id: str):
    request_id_var.set(req_id)


def get_request_id() -> str:
    return request_id_var.get() or "-"


class RequestIdLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.reqid = get_request_id()
        return True


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        incoming_id = request.headers.get("X-Request-ID")
        req_id = incoming_id or f"req-{uuid.uuid4()}"
        set_request_id(req_id)

        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = req_id
        return response


# class RequestIdMiddleware(BaseHTTPMiddleware):
#     async def dispatch(self, request: Request, call_next):
#         incoming_id = request.headers.get("X-Request-ID")
#         req_id = incoming_id or f"req-{uuid.uuid4()}"
#         set_request_id(req_id)

#         start_time = time.time()
#         response: Response = await call_next(request)
#         duration = time.time() - start_time

#         client_host = request.client.host if request.client else "unknown"
#         client_port = request.client.port if request.client else "unknown"

#         status_code = response.status_code
#         log_message = (
#             f'{client_host}:{client_port} - '
#             f'"{request.method} {request.url.path} HTTP/{request.scope.get("http_version","1.1")}" '
#             f'{status_code} - {duration:.4f}s'
#         )

#         if 200 <= status_code < 400:
#             LOG.info(log_message)
#         else:
#             LOG.error(log_message)

#         response.headers["X-Request-ID"] = req_id
#         return response


class QAAutoFileAccessMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, db_connection):
        super().__init__(app)
        self.db = db_connection

    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/qa-auto-files/"):
            deny = await self.validate_file_access(request)
            if deny:
                return deny
        return await call_next(request)

    async def validate_file_access(self, request: Request):
        path_parts = request.url.path.split('/')
        if len(path_parts) < 5:
            raise HTTPException(status_code=403, detail="Invalid path")

        requested_user = path_parts[2]

        current_user = await self.get_current_user(request)
        if not current_user:
            return Response("Authentication required", status_code=401)

        if requested_user != current_user:
            return Response("Access denied", status_code=403)

    async def get_current_user(self, request: Request) -> str:
        token = request.query_params.get("token")
        if token:
            try:
                payload = verify_token(token)
                user_id = payload.get("sub")
                if user_id:
                    return user_id
            except Exception:
                return None
        return None
