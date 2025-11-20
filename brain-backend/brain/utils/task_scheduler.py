# Copyright (C) 2021 - 2025, Shanghai Yunsilicon Technology Co., Ltd.
# All rights reserved.

from email.mime.text import MIMEText
import smtplib
import asyncio
from datetime import datetime
import logging
from typing import Dict, Callable

from brain.json_db import SQLiteDocumentDB
from brain.utils.ssh_client import ssh_execute

db = SQLiteDocumentDB()
SERVER_COLLECTION = "servers"
SMTP_HOST = "smtp.feishu.cn"
SMTP_PORT = 465
SMTP_USER = "wubl@yunsilicon.com"
SMTP_PASS = "199610wad14S.."

LOG = logging.getLogger(__name__)


class GenericTaskScheduler:
    """
    Generic task scheduler for handling delayed asynchronous tasks
    """

    def __init__(self):
        self.tasks: Dict[str, asyncio.Task] = {}

    async def schedule_task(
        self,
        task_id: str,
        delay_seconds: int,
        task_func: Callable,
        *args,
        **kwargs
    ) -> bool:
        """
        Schedule a delayed task

        Args:
            task_id: Unique task identifier
            delay_seconds: Delay time in seconds
            task_func: The function to be executed
            *args, **kwargs: Arguments passed to the task function

        Returns:
            bool: Whether the task was successfully scheduled
        """
        # Cancel any existing task with the same ID
        await self.cancel_task(task_id)

        try:
            # Create a new task
            task = asyncio.create_task(
                self._execute_after_delay(task_id, delay_seconds, task_func, *args, **kwargs)
            )
            self.tasks[task_id] = task

            LOG.info(f"Scheduled task '{task_id}' to run in {delay_seconds} seconds")
            return True

        except Exception as e:
            LOG.error(f"Failed to schedule task '{task_id}': {str(e)}")
            return False

    async def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a scheduled task

        Args:
            task_id: Unique task identifier

        Returns:
            bool: Whether the task was successfully canceled
        """
        if task_id in self.tasks:
            try:
                self.tasks[task_id].cancel()
                del self.tasks[task_id]
                LOG.info(f"Cancelled task: {task_id}")
                return True
            except Exception as e:
                LOG.error(f"Error cancelling task '{task_id}': {str(e)}")
                return False
        return False

    async def update_task(
        self,
        task_id: str,
        new_delay_seconds: int,
        task_func: Callable,
        *args,
        **kwargs
    ) -> bool:
        """
        Update the delay time of an existing scheduled task

        Args:
            task_id: Unique task identifier
            new_delay_seconds: New delay time in seconds
            task_func: The function to be executed
            *args, **kwargs: Arguments passed to the task function

        Returns:
            bool: Whether the task was successfully updated
        """
        return await self.schedule_task(task_id, new_delay_seconds, task_func, *args, **kwargs)

    async def _execute_after_delay(
        self,
        task_id: str,
        delay_seconds: int,
        task_func: Callable,
        *args,
        **kwargs
    ):
        """
        Execute a task after a delay
        """
        try:
            await asyncio.sleep(delay_seconds)

            # Run the actual task function
            result = await task_func(*args, **kwargs)

            LOG.info(f"Task '{task_id}' executed successfully")
            return result

        except asyncio.CancelledError:
            LOG.info(f"Task '{task_id}' was cancelled")
            raise
        except Exception as e:
            LOG.error(f"Error executing task '{task_id}': {str(e)}")
            raise
        finally:
            # Clean up completed tasks
            if task_id in self.tasks:
                del self.tasks[task_id]

    def task_exists(self, task_id: str) -> bool:
        """Check whether a task exists"""
        return task_id in self.tasks

    def get_running_tasks(self) -> list:
        """Get all currently running task IDs"""
        return list(self.tasks.keys())

    async def shutdown(self):
        """Shutdown the scheduler and cancel all tasks"""
        for task_id in list(self.tasks.keys()):
            await self.cancel_task(task_id)
        LOG.info("Task scheduler shut down")


task_scheduler = GenericTaskScheduler()


async def send_release_notification(to_email, server_ip):
    subject = "Server Released Notification"
    body = (
        "Hello,\n\n"
        "The server you were using has been released.\n"
        "Server IP: {}\n\n"
        "If this was not expected, please contact the administrator.\n\n"
        "Best regards,\n"
        "System Notification Service"
    ).format(server_ip)

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = f"{to_email}@yunsilicon.com"

    try:
        # use SSL (465)
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, [to_email], msg.as_string())
        return True
    except Exception as e:
        print("Error sending email:", str(e))
        return False


async def init_warning(ip, user, pwd):
    init_command = '''
sed -i '/# WARNING_MESSAGE_START/,/# WARNING_MESSAGE_END/d' /etc/profile

cat >> /etc/profile << 'EOF'
# WARNING_MESSAGE_START
echo "-----------------------------------------------------------------------------"
echo "提示：当前服务器无人使用！"
echo "请先登录: http://10.0.3.248:8089/devices 在[服务器管理]完成'占用服务器'后继续使用"
echo "-----------------------------------------------------------------------------"
# WARNING_MESSAGE_END
EOF
'''
    ssh_execute(ip, init_command, user, pwd)


async def occupy_warning(ip, ssh_user, ssh_pass, occupy_user, end_time):
    command = f'''
sed -i '/# WARNING_MESSAGE_START/,/# WARNING_MESSAGE_END/d' /etc/profile

cat >> /etc/profile << 'EOF'
# WARNING_MESSAGE_START
echo -e "\\033[5;31m"  # 闪烁红色
echo "██╗    ██╗ █████╗ ██████╗ ███╗   ██╗██╗██╗██╗"
echo "██║    ██║██╔══██╗██╔══██╗████╗  ██║██║██║██║"
echo "██║ █╗ ██║███████║██████╔╝██╔██╗ ██║██║██║██║"
echo "██║███╗██║██╔══██║██╔══██╗██║╚██╗██║╚═╝╚═╝╚═╝"
echo "╚███╔███╔╝██║  ██║██║  ██║██║ ╚████║██╗██╗██╗"
echo " ╚══╝╚══╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝╚═╝╚═╝"
echo -e "\\033[0m"  # 重置颜色
echo ""
echo "🚫 服务器已被占用！请立即退出！ 🚫"
echo "================================================"
echo "👤 使用人: {occupy_user}"
echo "⏰ 占用截止: {end_time}"
echo "🔗 管理页面: http://10.0.3.248:8089/devices"
echo ""
echo "💡 可登录管理页面，在[服务器管理]中查看其余可用服务器"
echo "================================================"
# WARNING_MESSAGE_END
EOF
'''
    ssh_execute(ip, command, ssh_user, ssh_pass)


async def init_server_warning(device_id: str):
    """
    Task function for initing up warning messages on a server
    """
    try:
        server = db.find_one(SERVER_COLLECTION, {"id": device_id})
        if not server:
            LOG.error(f"Device not found for cleanup: {device_id}")
            return

        old_user = server.get("user")
        # Execute cleanup command
        ip = server["device"]["ip"]
        ssh_user = server["device"].get("username", "")
        ssh_pass = server["device"].get("password", "")

        await init_warning(ip, ssh_user, ssh_pass)
        # Update database state
        server["time"] = 0
        server["user"] = ""
        server["start"] = ""
        server["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        db.update(SERVER_COLLECTION, {"id": device_id}, server)

        LOG.info(f"Automatically cleaned up warning messages for device: {device_id}")
        # if old_user:
        #     await send_release_notification(old_user, server["device"]["ip"])

    except Exception as e:
        LOG.error(f"Error in init_server_warning for {device_id}: {str(e)}")
        raise


async def setup_server_occupancy(device_id: str, user: str, duration: int):
    try:
        server = db.find_one(SERVER_COLLECTION, {"id": device_id})
        if not server:
            LOG.error(f"Device not found for occupancy setup: {device_id}")
            return False

        ip = server["device"]["ip"]
        ssh_user = server["device"].get("username", "")
        ssh_pass = server["device"].get("password", "")

        start_time = datetime.now().timestamp()
        end_timestamp = start_time + duration
        end_time = datetime.fromtimestamp(end_timestamp).strftime("%Y-%m-%d %H:%M:%S")

        await occupy_warning(ip, ssh_user, ssh_pass, user, end_time)

        # 更新数据库
        server["time"] = duration
        server["user"] = user
        server["start"] = start_time
        server["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        db.update(SERVER_COLLECTION, {"id": device_id}, server)

        LOG.info(f"Successfully set up occupancy for device {device_id} "
                 f"by user {user} for {duration} seconds")
        return True

    except Exception as e:
        LOG.error(f"Error setting up occupancy for device {device_id}: {str(e)}")
        return False