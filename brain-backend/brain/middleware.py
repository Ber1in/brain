# Copyright (C) 2021 - 2025, Shanghai Yunsilicon Technology Co., Ltd.
# All rights reserved.

from datetime import datetime
import logging
import uuid
from contextvars import ContextVar

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from brain.auth import verify_token
from brain.json_db import db

LOG = logging.getLogger(__name__)
OPERATIONAL_AUDIT_COLLECTION = "operational_audit"
NON_AUDITED_OPERATIONS_PREFIX = (
    "/login", "/api/filtering_conditions", "/api/yuntester", "/api/tag")
NON_AUDITED_OPERATIONS_SUFFIX = ("follow", "occupy", "release")


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
        req_id = request.headers.get("X-Request-ID") or f"req-{uuid.uuid4()}"
        set_request_id(req_id)

        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = req_id

        try:
            username = self.get_current_user(request.headers.get("authorization"))
            if not username:
                username = request.headers.get("X-User", "")

            path = request.url.path
            should_skip = path.startswith(NON_AUDITED_OPERATIONS_PREFIX) or path.endswith(
                NON_AUDITED_OPERATIONS_SUFFIX)
            if not should_skip and request.method != "GET":
                db.insert(
                    OPERATIONAL_AUDIT_COLLECTION,
                    {
                        "request_id": req_id,
                        "user": username,
                        "path": path,
                        "method": request.method,
                        "status": response.status_code,
                        "date": date
                    }
                )
        except Exception as e:
            LOG.error(f"Failed to insert audit record for {req_id}: {e}")

        return response

    def get_current_user(self, token: str) -> str:
        if not token:
            return ""

        if token.startswith("Bearer "):
            token = token[len("Bearer "):].strip()

        try:
            payload = verify_token(token)
            return payload.get("sub", "")
        except Exception:
            return ""


