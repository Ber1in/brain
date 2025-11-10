# Copyright (C) 2021 - 2025, Shanghai Yunsilicon Technology Co., Ltd.
# All rights reserved.

import asyncio
from datetime import datetime
import logging
from typing import Dict, Callable

from brain.json_db import SQLiteDocumentDB
from brain.utils.ssh_client import ssh_execute

db = SQLiteDocumentDB()
SERVER_COLLECTION = "servers"

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


async def init_warning(ip, user, pwd):
    clean_command = '''
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
    ssh_execute(ip, clean_command, user, pwd)


async def occupy_warning(ip, ssh_user, ssh_pass, occupy_user, end_time):
    command = f'''
sed -i '/# WARNING_MESSAGE_START/,/# WARNING_MESSAGE_END/d' /etc/profile

cat >> /etc/profile << 'EOF'
# WARNING_MESSAGE_START
echo "--------------------------------------------------------------------"
echo "警告：当前服务器有人正在使用！请勿执行破坏性操作！"
echo "使用人: {occupy_user}"
echo "占用截止时间: {end_time}"
echo "请登录: http://10.0.3.248:8089/devices 在[服务器管理]页面查看其余可用服务器"
echo "--------------------------------------------------------------------"
# WARNING_MESSAGE_END
EOF
'''
    ssh_execute(ip, command, ssh_user, ssh_pass)


async def cleanup_server_warning(device_id: str):
    """
    Task function for cleaning up warning messages on a server
    """
    try:
        server = db.find_one(SERVER_COLLECTION, {"id": device_id})
        if not server:
            LOG.error(f"Device not found for cleanup: {device_id}")
            return

        # Execute cleanup command
        ip = server["device"]["ip"]
        ssh_user = server["device"].get("username", "")
        ssh_pass = server["device"].get("password", "")

        init_warning(ip, ssh_user, ssh_pass)
        # Update database state
        server["time"] = 0
        server["user"] = ""
        server["start"] = ""
        server["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        db.update(SERVER_COLLECTION, {"id": device_id}, server)

        LOG.info(f"Automatically cleaned up warning messages for device: {device_id}")

    except Exception as e:
        LOG.error(f"Error in cleanup_server_warning for {device_id}: {str(e)}")
        raise


async def setup_server_occupancy(device_id: str, user: str, duration: int):
    """
    设置服务器占用的任务函数
    """
    try:
        server = db.find_one(SERVER_COLLECTION, {"id": device_id})
        if not server:
            LOG.error(f"Device not found for occupancy setup: {device_id}")
            return False

        ip = server["device"]["ip"]
        ssh_user = server["device"].get("username", "")
        ssh_pass = server["device"].get("password", "")

        # 计算结束时间
        start_time = datetime.now().timestamp()
        end_timestamp = start_time + duration
        end_time = datetime.fromtimestamp(end_timestamp).strftime("%Y-%m-%d %H:%M:%S")

        # 设置警告信息
        occupy_warning(ip, ssh_user, ssh_pass, user, end_time)

        # 更新数据库
        server["time"] = duration
        server["user"] = user
        server["start"] = start_time
        server["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        db.update(SERVER_COLLECTION, {"id": device_id}, server)

        LOG.info(
            f"Successfully set up occupancy for device {device_id} by user {user} for {duration} seconds")
        return True

    except Exception as e:
        LOG.error(f"Error setting up occupancy for device {device_id}: {str(e)}")
        return False