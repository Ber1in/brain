# Copyright (C) 2021 - 2025, Shanghai Yunsilicon Technology Co., Ltd.
# All rights reserved.

import logging
import uuid
from contextvars import ContextVar

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

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
