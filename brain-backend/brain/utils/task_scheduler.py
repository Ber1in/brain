# Copyright (C) 2021 - 2025, Shanghai Yunsilicon Technology Co., Ltd.
# All rights reserved.


import json
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
import smtplib
import asyncio
from datetime import datetime
import logging
from typing import Dict, Callable

from brain.json_db import SQLiteDocumentDB
from brain.utils.ssh_client import ssh_execute

db = SQLiteDocumentDB()
SERVER_COLLECTION = "servers"
WEBHOOK_URL = (
    "https://webhook.yunsilicon.com/open-apis/bot/v2/hook/860b5b73-c26f-4520-91be-d13c4f57a2e3")
SMTP_CONFIG = {
    "host": "smtp.feishu.cn",
    "port": 465,
    "user": "yuntester@yunsilicon.com",
    "password": "VIgB7YFDX9Y3g7Dw"
}
YUNTESTER_PLOTFORM = "https://yuntester.yunsilicon.com/devices"


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


async def init_warning(ip, user, pwd):
    init_command = '''
sed -i '/# WARNING_MESSAGE_START/,/# WARNING_MESSAGE_END/d' /etc/profile

cat >> /etc/profile << 'EOF'
# WARNING_MESSAGE_START
echo "-----------------------------------------------------------------------------"
echo "提示：当前服务器无人使用！"
echo "请先登录: https://yuntester.yunsilicon.com/devices 在[服务器管理]完成'占用服务器'后继续使用"
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
echo "🔗 管理页面: https://yuntester.yunsilicon.com/devices"
echo ""
echo "💡 可登录管理页面，在[服务器管理]中查看其余可用服务器"
echo "================================================"
# WARNING_MESSAGE_END
EOF
'''
    ssh_execute(ip, command, ssh_user, ssh_pass)


async def init_server_warning(device_id: str, now=False):
    """
    Task function for initing up warning messages on a server
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

        # Update database state
        send_feishu_group_message(server, now)
        send_server_reminder(server, now)
        if now:
            await init_warning(ip, ssh_user, ssh_pass)
            server["time"] = 0
            server["user"] = ""
            server["start"] = ""
            server["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            db.update(SERVER_COLLECTION, {"id": device_id}, server)

        LOG.info(f"Automatically cleaned up warning messages for device: {ip}")

    except Exception as e:
        LOG.warning(f"Error in init_server_warning for {ip}: {str(e)}")


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


def send_feishu_group_message(server_info, now=False):
    """
    Send Feishu group reminder message.
    The message content remains in Chinese (intended for end users).
    """
    try:
        # 根据 now 参数决定消息内容
        if now:
            title = f"🖥️ 服务器已释放 - {server_info['device']['ip']}"
            content_lines = [
                f"**服务器IP:** {server_info['device']['ip']}",
                f"**原占用人:** {server_info['user']}",
                f"**释放时间:** ✅ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                "**当前状态:** 🆓 空闲可用"
            ]
            note_text = "📋 服务器已释放，现在可以重新分配使用"
            template = "green"  # 绿色表示已完成
        else:
            title = f"🖥️ 服务器占用到期提醒 - {server_info['device']['ip']}"
            content_lines = [
                f"**服务器IP:** {server_info['device']['ip']}",
                f"**占用人:** {server_info['user']}",
                "**剩余时间:** 🚨 5分钟"
            ]
            note_text = "📋 请登录管理页面，在【服务器管理】中查看其余可用服务器"
            template = "red"  # 红色表示紧急

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
                        "content": title
                    },
                    "template": template
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": "\n".join(content_lines)
                        }
                    },
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": (
                                f"**关注人数:** 👥 {len(server_info.get('recipients', []))}人"
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
                                "url": YUNTESTER_PLOTFORM
                            }
                        ]
                    },
                    {
                        "tag": "note",
                        "elements": [
                            {
                                "tag": "plain_text",
                                "content": (
                                    f"{note_text}\n"
                                    f"发送时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                                )
                            }
                        ]
                    }
                ]
            }
        }

        # Send Feishu request
        headers = {'Content-Type': 'application/json'}
        response = requests.post(WEBHOOK_URL, headers=headers, data=json.dumps(message_content))

        if response.status_code == 200:
            result = response.json()
            if result.get("code") == 0:
                action = "cleanup" if now else "warning"
                LOG.info(f"Feishu {action} message sent successfully.")
                return True
            LOG.error(f"Feishu message failed: {result}")
            return False

        LOG.error(f"Feishu message failed with status code: {response.status_code}")
        return False

    except Exception as e:
        LOG.error(f"Feishu message exception: {e}")
        return False


def create_server_reminder_email(server_info, current_recipient, now=False):
    """
    Create personalized email reminder for server expiration.
    Email content remains Chinese because it's user-facing.
    """
    # Determine whether the recipient is the server owner
    is_owner = current_recipient.split('@')[0].lower() == server_info['user'].lower()

    if now:
        # 已释放的通知
        reminder_title = f"🖥️ 服务器释放通知 - {server_info['device']['ip']}"
        if is_owner:
            reminder_text = "您占用的服务器已按时释放"
        else:
            reminder_text = "您关注的服务器已释放"
        status_info = "已释放"
        status_class = "released"  # 可以添加不同的样式类
        operation_guide = "服务器现已空闲，可供重新分配使用"
    else:
        # 即将到期的提醒
        reminder_title = f"🖥️ 服务器占用到期提醒 - {server_info['device']['ip']}"
        if is_owner:
            reminder_text = "您的服务器占用即将到期，请及时处理"
        else:
            reminder_text = "您关注的服务器占用即将到期，请及时处理"
        status_info = "5分钟"
        status_class = "urgent"
        operation_guide = "请及时处理服务器续期或释放资源" if is_owner else "请关注服务器状态变化"

    # Email subject
    subject = f"{reminder_title.split(' ')[1]} - {server_info['device']['ip']}"

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
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
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
            .highlight {{
                background-color: #fff8e1;
                padding: 15px;
                border-left: 4px solid #ffc107;
                margin: 20px 0;
                border-radius: 4px;
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
            .urgent {{
                color: #e74c3c;
                font-weight: bold;
            }}
            .released-status {{
                color: #4CAF50;
                font-weight: bold;
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
                <h1>{reminder_title}</h1>
                <p>{reminder_text}</p>
            </div>

            <h2>服务器信息</h2>
            <table class="info-table">
                <tr><td>服务器IP:</td><td><strong>{server_info['device']['ip']}</strong></td></tr>
                <tr><td>{'原占用人:' if now else '占用人:'}</td><td><strong>{server_info['user']}</strong>{('<span class="owner-badge">您</span>' if is_owner else '')}</td></tr>
                <tr><td>{'释放时间:' if now else '剩余时间:'}</td><td class="{status_class}">{status_info}</td></tr>
            </table>

            <div class="highlight">
                <strong>📋 操作指引:</strong><br>
                {operation_guide}<br>
                登录管理页面，在<strong>【服务器管理】</strong>中查看详情
            </div>

            <p>
                <a href="{YUNTESTER_PLOTFORM}" class="button">
                    🔗 登录管理页面
                </a>
            </p>

            <div class="footer">
                <p>此邮件由系统自动发送，请勿直接回复</p>
                <p>发送时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p>收件人: {current_recipient} | 总关注人数: {len(server_info.get('recipients', []))}</p>
                <p>如有问题，请联系系统管理员</p>
            </div>
        </div>
    </body>
    </html>
    """  # noqa

    # Build MIME message
    msg = MIMEMultipart('alternative')
    msg['From'] = Header(SMTP_CONFIG['user'])
    msg['To'] = Header(current_recipient)
    msg['Subject'] = Header(subject)

    # Attach HTML content
    msg.attach(MIMEText(html_content, 'html', 'utf-8'))
    return msg


def send_server_reminder(server_info, now=False):
    """
    Send server expiration reminder emails to all recipients.
    """
    success_count = 0
    total_count = len(server_info.get("recipients", []))

    # Send email to each recipient
    for recipient in server_info.get("recipients", []):
        try:
            # Create personalized email for each recipient
            msg = create_server_reminder_email(server_info, recipient, now)

            # Send via SMTP
            with smtplib.SMTP_SSL(SMTP_CONFIG['host'], SMTP_CONFIG['port']) as server_smtp:
                server_smtp.login(SMTP_CONFIG['user'], SMTP_CONFIG['password'])
                server_smtp.sendmail(
                    SMTP_CONFIG['user'], [f'{recipient}@yunsilicon.com'], msg.as_string())

            # Check ownership for proper logging
            is_owner = recipient.split('@')[0].lower() == server_info['user'].lower()
            action = "cleanup" if now else "warning"
            role = "Owner" if is_owner else "Follower"
            LOG.info(f"{role} {action} email sent successfully: {recipient}")

            success_count += 1

        except Exception as e:
            LOG.error(f"Email failed to: {recipient}, error: {e}")

    action = "cleanup" if now else "warning"
    LOG.info(f"{action} email summary: success {success_count}/{total_count}")

    return success_count == total_count