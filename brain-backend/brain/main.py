# Copyright (C) 2021 - 2025, Shanghai Yunsilicon Technology Co., Ltd.
# All rights reserved.

from datetime import datetime
import logging
import os

from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles

from brain import app
from brain.config import settings
from brain.api.register import register_routers
from brain import middleware  # noqa: F401
from brain.middleware import RequestIdLogFilter, RequestIdMiddleware, QAAutoFileAccessMiddleware
from brain.json_db import SQLiteDocumentDB
from brain.utils.task_scheduler import init_server_warning, task_scheduler

LOG_FILE = "/var/log/brain/brain.log"
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
db = SQLiteDocumentDB()
SERVER_COLLECTION = "servers"


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
uvicorn_access_logger.setLevel(logging.WARN)

register_routers(app)


@app.on_event("startup")
async def startup_event():
    """Restore pending scheduled tasks at startup"""
    try:
        # Find all occupied devices
        occupied_servers = db.find(SERVER_COLLECTION, {"time >": 0})
        logger.info(f"Found {len(occupied_servers)} occupied devices to restore timers")

        for server in occupied_servers:
            # Calculate remaining time
            elapsed_time = datetime.now().timestamp() - server["start"]
            remaining_time = server["time"] - elapsed_time

            ip: str = server['device']['ip']
            if remaining_time > 0:
                # Restore scheduled task

                warn_delay = max(remaining_time - 300, 0)
                if warn_delay > 0:
                    warn_task_id = f"device_warn_{ip.replace('.', '_')}"
                    warn_success = await task_scheduler.schedule_task(
                        task_id=warn_task_id,
                        delay_seconds=warn_delay,
                        task_func=init_server_warning,
                        device_id=server["id"],
                    )
                    if warn_success:
                        logger.info(
                            f"Scheduled warning task {warn_task_id} "
                            f"(delay={warn_delay}s)"
                        )
                    else:
                        logger.error(f"Failed to schedule warning task {warn_task_id}")

                task_id = f"device_cleanup_{ip.replace('.', '_')}"
                success = await task_scheduler.schedule_task(
                    task_id=task_id,
                    delay_seconds=int(remaining_time),
                    task_func=init_server_warning,
                    device_id=server["id"],
                    now=True
                )

                if success:
                    logger.info(
                        f"Restored timer for device {ip}, "
                        f"remaining: {remaining_time:.0f}s"
                    )
                else:
                    logger.error(f"Failed to restore timer for device {ip}")
            else:
                # If the time has already expired, clean up immediately
                logger.info(f"Device {ip} occupancy expired, cleaning up...")
                await init_server_warning(server["id"], True)

    except Exception as e:
        logger.error(f"Error while restoring device timers: {str(e)}")


app.add_middleware(QAAutoFileAccessMiddleware, db_connection=db)
app.mount("/qa-auto-files", StaticFiles(directory="/opt/yunTesterData"), name="qa-auto-files")


def main():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.platform_port)


if __name__ == "__main__":
    main()
