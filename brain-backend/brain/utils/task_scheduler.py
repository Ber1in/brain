# Copyright (C) 2021 - 2025, Shanghai Yunsilicon Technology Co., Ltd.
# All rights reserved.


import aiohttp
from enum import Enum
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
import smtplib
import asyncio
from datetime import datetime
import logging
from typing import Dict, Callable

from brain.json_db import SQLiteDocumentDB
from brain.utils.ssh_client import ssh_execute_async
from brain.config import settings

db = SQLiteDocumentDB()
SERVER_COLLECTION = "servers"


LOG = logging.getLogger(__name__)


class ServerStatus(str, Enum):
    OCCUPIED = "occupied"
    EXPIRING = "expiring"
    RELEASED = "released"


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

            LOG.info(f"Task {task_id} executed successfully")
            return result

        except asyncio.CancelledError:
            LOG.info(f"Task {task_id} was cancelled")
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


def get_end_time_display(server_info):
    if server_info.get('time'):
        end_timestamp = datetime.now().timestamp() + int(server_info['time'])
        return datetime.fromtimestamp(end_timestamp).strftime('%Y-%m-%d %H:%M:%S')
    return ""


async def _try_init_warning(ip, user, pwd):
    init_command = f'''
sed -i '/# WARNING_MESSAGE_START/,/# WARNING_MESSAGE_END/d' /etc/profile

cat >> /etc/profile << 'EOF'
# WARNING_MESSAGE_START
echo "-----------------------------------------------------------------------------"
echo "提示：当前服务器无人使用！"
echo "请先登录: {settings.yuntester_platform}/devices 在[服务器管理]完成'占用服务器'后继续使用"
echo "-----------------------------------------------------------------------------"
# WARNING_MESSAGE_END
EOF
'''
    try:
        await ssh_execute_async(ip, init_command, user, pwd, False)
    except Exception:
        LOG.warning(
            f"The server {ip} is offline and the init_warning process has not been completed")


async def init_warning(ip, user, pwd):
    asyncio.create_task(_try_init_warning(ip, user, pwd))


async def _try_occupy_warning(ip, ssh_user, ssh_pass, occupy_user, end_time):
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
echo "🔗 管理页面: {settings.yuntester_platform}/devices"
echo ""
echo "💡 可登录管理页面，在[服务器管理]中查看其余可用服务器"
echo "================================================"
# WARNING_MESSAGE_END
EOF
'''
    try:
        await ssh_execute_async(ip, command, ssh_user, ssh_pass, False)
    except Exception:
        LOG.warning(f"The server {ip} is offline and the occupy_warning"
                    " process has not been completed")


async def occupy_warning(ip, ssh_user, ssh_pass, occupy_user, end_time):
    asyncio.create_task(_try_occupy_warning(ip, ssh_user, ssh_pass, occupy_user, end_time))


async def init_server_warning(device_id: str, status: ServerStatus):
    """
    Task function for sending server status notifications
    """
    try:
        server = db.find_one(SERVER_COLLECTION, {"id": device_id})
        if not server:
            LOG.error(f"Device not found: {device_id}")
            return

        ip = server["device"]["ip"]
        ssh_user = server["device"].get("username", "")
        ssh_pass = server["device"].get("password", "")

        await send_server_reminder(server, status)
        await send_feishu_group_message(server, status)

        if status == ServerStatus.RELEASED:
            await init_warning(ip, ssh_user, ssh_pass)
            server["time"] = 0
            server["user"] = ""
            server["start"] = ""
            server["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            db.update(SERVER_COLLECTION, {"id": device_id}, server)

        LOG.info(f"Sent {status.value} notification for device: {ip}")

    except Exception as e:
        LOG.warning(f"Error in init_server_warning for {device_id}: {str(e)}")


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


async def send_feishu_group_message(server_info, status: ServerStatus):
    """
    Send Feishu group reminder message.
    """
    try:
        # 根据状态设置不同的消息内容
        status_configs = {
            ServerStatus.OCCUPIED: {
                "title": f"🖥️ 服务器已被占用 - {server_info['device']['ip']}",
                "template": "blue",
                "content_lines": [
                    f"**占用人:** 👤 {server_info['user']}",
                    f"**截止时间:** ⏰ {get_end_time_display(server_info)}",
                    f"**服务器:** 🖥️ {server_info['bmc']['hostname']}"
                ],
                "note_text": "📋 服务器已被占用，请在占用期间合理使用"
            },
            ServerStatus.EXPIRING: {
                "title": f"🖥️ 服务器占用到期提醒 - {server_info['device']['ip']}",
                "template": "red",
                "content_lines": [
                    f"**占用人:** 👤 {server_info['user']}",
                    "**剩余时间:** 🚨 5分钟",
                    f"**服务器:** 🖥️ {server_info['bmc']['hostname']}"
                ],
                "note_text": "📋 请及时处理服务器续期或释放"
            },
            ServerStatus.RELEASED: {
                "title": f"🖥️ 服务器已释放 - {server_info['device']['ip']}",
                "template": "green",
                "content_lines": [
                    f"**原占用人:** 👤 {server_info['user']}",
                    f"**释放时间:** ✅ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    f"**服务器:** 🖥️ {server_info['bmc']['hostname']}",
                    "**当前状态:** 🆓 空闲可用"
                ],
                "note_text": "📋 服务器已释放，现在可以重新分配使用"
            }
        }

        config = status_configs[status]

        # Build Feishu interactive card payload
        message_content = {
            "msg_type": "interactive",
            "card": {
                "config": {
                    "wide_screen_mode": True
                },
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": config["title"]
                    },
                    "template": config["template"]
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": "\n".join(config["content_lines"])
                        }
                    },
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": (
                                f"**关注人:** 👥 {server_info.get('recipients', [])}"
                            )
                        }
                    },
                    {
                        "tag": "action",
                        "actions": [
                            {
                                "tag": "button",
                                "text": {"tag": "plain_text", "content": "🔗 登录管理页面"},
                                "type": "primary",
                                "url": f"{settings.yuntester_platform}/devices"
                            }
                        ]
                    },
                    {
                        "tag": "note",
                        "elements": [
                            {
                                "tag": "plain_text",
                                "content": (
                                    f"{config['note_text']}\n"
                                    f"发送时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                                )
                            }
                        ]
                    }
                ]
            }
        }

        async def send_feishu_async(webhook: str, payload: dict, status: ServerStatus) -> bool:
            try:
                timeout = aiohttp.ClientTimeout(
                    connect=5,       # 连接超时5秒
                    sock_connect=5,  # socket连接超时5秒
                    total=None       # 不设置总超时，让请求在后台完成
                )
                
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    try:
                        async with session.post(webhook, json=payload):
                            LOG.info(f"Feishu message sent (fire-and-forget), webhook: {webhook}")
                            return True
                    except asyncio.TimeoutError:
                        LOG.warning(f"Feishu connection timeout, but request may have been sent")
                        return True
                            
            except aiohttp.ClientError as e:
                LOG.error(f"Feishu connection error: {e}")
                return False
            except Exception as e:
                LOG.error(f"Feishu message exception: {e}")
                return False

        # Send Feishu request
        release_notices = settings.release_notices
        matched_webhooks = [
            notice.webhook
            for notice in release_notices
            if notice.tag in server_info["tags"]
        ]

        if not matched_webhooks:
            matched_webhooks = [settings.default_webhook]

        tasks = []
        for webhook in matched_webhooks:
            task = asyncio.create_task(
                send_feishu_async(webhook, message_content, status)
            )
            tasks.append(task)

        try:
            done, pending = await asyncio.wait(tasks, timeout=65)

            for task in done:
                try:
                    result = task.result()
                    if not result:
                        LOG.warning("Feishu message failed for one webhook")
                except Exception as e:
                    LOG.error(f"Task exception: {e}")

            for task in pending:
                task.cancel()

        except asyncio.TimeoutError:
            LOG.warning("Some Feishu messages timed out during gathering")
            for task in tasks:
                if not task.done():
                    task.cancel()

    except Exception as e:
        LOG.error(f"Feishu message exception: {e}")


async def create_server_reminder_email(server_info, current_recipient, status: ServerStatus):
    """
    Create personalized email reminder for server status changes.
    Email content remains Chinese because it's user-facing.
    """
    # Determine whether the recipient is the server owner
    is_owner = current_recipient.split('@')[0].lower() == server_info['user'].lower()

    status_configs = {
        ServerStatus.OCCUPIED: {
            "title": f"🖥️ 服务器占用通知 - {server_info['device']['ip']}",
            "owner_text": "您已成功占用服务器",
            "follower_text": "您关注的服务器已被占用",
            "time_info": (
                f"截止时间: {get_end_time_display(server_info)}" if server_info.get('time') else ""),
            "status_text": "已占用",
            "status_class": "occupied",
            "operation_guide": "请在占用期间合理使用服务器资源",
            "template_color": "#2196F3"
        },
        ServerStatus.EXPIRING: {
            "title": f"🖥️ 服务器占用到期提醒 - {server_info['device']['ip']}",
            "owner_text": "您的服务器占用即将到期，请及时处理",
            "follower_text": "您关注的服务器占用即将到期",
            "time_info": "剩余时间: 5分钟",
            "status_text": "即将到期",
            "status_class": "urgent",
            "operation_guide": "请及时处理服务器续期或释放资源" if is_owner else "请关注服务器状态变化",
            "template_color": "#FF9800"
        },
        ServerStatus.RELEASED: {
            "title": f"🖥️ 服务器释放通知 - {server_info['device']['ip']}",
            "owner_text": "您占用的服务器已按时释放",
            "follower_text": "您关注的服务器已释放",
            "time_info": f"释放时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "status_text": "已释放",
            "status_class": "released",
            "operation_guide": "服务器现已空闲，可供重新分配使用",
            "template_color": "#4CAF50"
        }
    }

    config = status_configs[status]
    reminder_text = config["owner_text"] if is_owner else config["follower_text"]

    # Email subject
    subject = f"{config['title'].split(' ')[1]} - {server_info['device']['ip']}"

    show_occupier = status != ServerStatus.RELEASED

    # HTML content (Chinese)
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{
                font-family: 'Microsoft YaHei', Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                margin: 0;
                padding: 20px;
                background-color: #f5f5f5;
            }}
            .container {{
                max-width: 600px;
                margin: 0 auto;
                background: white;
                padding: 30px;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            .header {{
                background: linear-gradient(135deg, {config['template_color']} 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                border-radius: 8px 8px 0 0;
                margin: -30px -30px 20px -30px;
            }}
            .info-table {{
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
            }}
            .info-table td {{
                padding: 12px;
                border-bottom: 1px solid #eee;
            }}
            .info-table td:first-child {{
                font-weight: bold;
                width: 120px;
                color: #666;
            }}
            .occupied {{
                background-color: #e8f4fd;
                padding: 15px;
                border-left: 4px solid #2196F3;
                margin: 20px 0;
                border-radius: 4px;
                color: #2196F3;
                font-weight: bold;
            }}
            .urgent {{
                background-color: #fff8e1;
                padding: 15px;
                border-left: 4px solid #ffc107;
                margin: 20px 0;
                border-radius: 4px;
                color: #e74c3c;
                font-weight: bold;
            }}
            .released {{
                background-color: #e8f5e8;
                padding: 15px;
                border-left: 4px solid #4CAF50;
                margin: 20px 0;
                border-radius: 4px;
                color: #2e7d32;
                font-weight: bold;
            }}
            .personal-note {{
                background-color: #e8f4fd;
                padding: 15px;
                border-left: 4px solid #2196F3;
                margin: 20px 0;
                border-radius: 4px;
            }}
            .footer {{
                margin-top: 30px;
                padding-top: 20px;
                border-top: 1px solid #eee;
                color: #666;
                font-size: 12px;
            }}
            .button {{
                display: inline-block;
                background: #667eea;
                color: white;
                padding: 12px 24px;
                text-decoration: none;
                border-radius: 4px;
                margin: 10px 0;
            }}
            .owner-badge {{
                background: #e74c3c;
                color: white;
                padding: 2px 8px;
                border-radius: 12px;
                font-size: 12px;
                margin-left: 8px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>{config['title']}</h1>
                <p>{reminder_text}</p>
            </div>

            <h2>服务器信息</h2>
            <table class="info-table">
                <tr><td>服务器IP:</td><td><strong>{server_info['device']['ip']}</strong></td></tr>
                {"<tr><td>{}:</td><td><strong>{}</strong>{}</td></tr>".format(
                    "占用人" if show_occupier else "原占用人",
                    server_info["user"],
                    '<span class="owner-badge">您</span>' if is_owner else ""
                ) if server_info.get("user") else ""}
                <tr><td>状态:</td><td class="{config['status_class']}">{config['status_text']}</td></tr>
                {"<tr><td>时间信息:</td><td>{}</td></tr>".format(config['time_info']) if config['time_info'] else ""}
                {"<tr><td>服务器名称:</td><td>{}</td></tr>".format(server_info['bmc']['hostname']) if server_info.get('bmc', {}).get('hostname') else ""}
            </table>

            <div class="{config['status_class']}">
                <strong>📋 操作指引:</strong><br>
                {config['operation_guide']}<br>
                登录管理页面，在<strong>【服务器管理】</strong>中查看详情
            </div>

            <p>
                <a href="{settings.yuntester_platform}/devices" class="button">
                    🔗 登录管理页面
                </a>
            </p>

            <div class="footer">
                <p>此邮件由系统自动发送，请勿直接回复</p>
                <p>发送时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p>收件人: {current_recipient} | 关注人: {server_info.get('recipients', [])}</p>
                <p>如有问题，请联系系统管理员</p>
            </div>
        </div>
    </body>
    </html>
    """  # noqa

    # Build MIME message
    msg = MIMEMultipart('alternative')
    msg['From'] = Header(settings.smtp.user)
    msg['To'] = Header(current_recipient)
    msg['Subject'] = Header(subject)

    # Attach HTML content
    msg.attach(MIMEText(html_content, 'html', 'utf-8'))
    return msg


async def send_server_reminder(server_info, status: ServerStatus):
    """
    Fire-and-forget server status change email notifications.
    """

    messages = []

    for recipient in server_info.get("recipients", []):
        if recipient == "admin":
            continue

        try:
            msg = await create_server_reminder_email(server_info, recipient, status)
            messages.append((recipient, msg))
        except Exception as e:
            LOG.error(f"Create email failed for {recipient}: {e}")

    def _send_server_reminder_sync(messages, status: ServerStatus):
        for recipient, msg in messages:
            try:
                with smtplib.SMTP_SSL(
                    settings.smtp.host,
                    settings.smtp.port,
                    timeout=15
                ) as server_smtp:
                    server_smtp.login(settings.smtp.user, settings.smtp.password)
                    server_smtp.sendmail(
                        settings.smtp.user,
                        [f'{recipient}@yunsilicon.com'],
                        msg.as_string()
                    )

                LOG.info(f"{status.value} email sent: {recipient}")

            except Exception as e:
                LOG.error(f"Email failed to {recipient}: {e}")

    asyncio.get_running_loop().run_in_executor(
        None,
        _send_server_reminder_sync,
        messages,
        status
    )