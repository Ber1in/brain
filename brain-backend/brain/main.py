# Copyright (C) 2021 - 2025, Shanghai Yunsilicon Technology Co., Ltd.
# All rights reserved.

import logging
import os

from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from brain import app
from brain.api.register import register_routers
from brain import middleware  # noqa: F401
from brain.middleware import RequestIdLogFilter, RequestIdMiddleware

LOG_FILE = "/var/log/brain/brain.log"
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

register_routers(app)


@app.exception_handler(Exception)
async def handle_500_exception(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "detail": str(exc)
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(req: Request, exc: RequestValidationError):
    logger.error(f"422 Unprocessable Entity: {exc.errors()}, Request body: {exc.body}")

    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )


class FsyncFileHandler(logging.FileHandler):
    def emit(self, record):
        super().emit(record)
        self.flush()
        os.fsync(self.stream.fileno())


app.add_middleware(RequestIdMiddleware)
request_id_filter = RequestIdLogFilter()
log_format = '%(asctime)s [%(levelname)s] [%(reqid)s] %(pathname)s:%(lineno)d: %(message)s'

file_handler = FsyncFileHandler(LOG_FILE)
file_handler.setFormatter(logging.Formatter(log_format))
file_handler.addFilter(request_id_filter)

logger = logging.getLogger("brain")
logger.handlers.clear()
logger.addHandler(file_handler)
logger.addFilter(request_id_filter)
logger.setLevel(logging.INFO)

uvicorn_logger = logging.getLogger("uvicorn")
uvicorn_logger.handlers.clear()
uvicorn_logger.addHandler(file_handler)
uvicorn_logger.addFilter(request_id_filter)
uvicorn_logger.setLevel(logging.INFO)

uvicorn_access_logger = logging.getLogger("uvicorn.access")
uvicorn_access_logger.handlers.clear()
uvicorn_access_logger.addHandler(file_handler)
uvicorn_access_logger.addFilter(request_id_filter)
uvicorn_access_logger.setLevel(logging.INFO)
