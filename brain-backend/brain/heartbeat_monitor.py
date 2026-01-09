# Copyright (C) 2021 - 2025, Shanghai Yunsilicon Technology Co., Ltd.
# All rights reserved.

import asyncio
import logging
from datetime import datetime

from brain.json_db import SQLiteDocumentDB
from brain.config import settings
from brain.utils import common_utils
from brain.utils.ssh_client import ssh_execute_async

db = SQLiteDocumentDB()
SERVER_COLLECTION = "servers"
LOG = logging.getLogger(__name__)


class HeartbeatMonitor:
    def __init__(self):
        self.check_interval = 60
        self.heartbeat_timeout = 180
        self.monitoring_tasks = {}

    async def start_monitoring(self):
        """Start heartbeat monitoring loop"""
        LOG.info("Heartbeat monitor started")
        while settings.check_heartbeat:
            try:
                await self.check_all_servers()
            except Exception as e:
                LOG.debug(f"Heartbeat monitor loop error: {e}")
            await asyncio.sleep(self.check_interval)

    async def check_all_servers(self):
        """Check heartbeat status for all servers"""
        servers = db.find(SERVER_COLLECTION)

        now = datetime.now()

        for server in servers:
            ip = server["device"]["ip"]
            last_heartbeat_str = server.get("last_heartbeat")

            last_heartbeat = None
            if last_heartbeat_str:
                try:
                    last_heartbeat = datetime.strptime(last_heartbeat_str, "%Y-%m-%d %H:%M:%S.%f")
                except ValueError:
                    LOG.debug(f"Server {ip} has invalid last_heartbeat format: "
                              f"{last_heartbeat_str}")

            if (
                not last_heartbeat_str or (
                    last_heartbeat and (
                        now - last_heartbeat).total_seconds() > self.heartbeat_timeout)
            ):
                elapsed = (None if not last_heartbeat else (now - last_heartbeat).total_seconds())

                LOG.debug(f"Heartbeat timeout detected for server {ip} "
                          f"(last={last_heartbeat}, elapsed={elapsed}s)")

                await self.handle_heartbeat_timeout(server)

    def generate_systemd_service(self, server_id: str) -> str:
        """生成 systemd service 文件内容"""
        return f"""[Unit]
Description=Server Heartbeat Daemon for {server_id}
After=network.target

[Service]
Type=simple
User=root
Environment=SERVER_ID={server_id}
Environment=API_ENDPOINT=https://yuntester.yunsilicon.com/api
WorkingDirectory=/opt/server_daemon
ExecStart=/opt/server_daemon/server_daemon.sh --server-id {server_id}
ExecStop=/bin/kill -TERM $MAINPID
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
"""

    async def handle_heartbeat_timeout(self, server: dict):
        """Handle heartbeat timeout for a server"""
        server_id = server["id"]
        ip = server["device"]["ip"]

        try:
            db.update(SERVER_COLLECTION, {"id": server_id}, {"status": "offline"})

            LOG.info(f"Server {ip} marked as offline, attempting daemon injection")

            success = await self.inject_daemon(server)

            if success:
                LOG.debug(f"Daemon injection succeeded for server {ip}")
            else:
                LOG.debug(f"Daemon injection failed for server {ip}")

        except Exception as e:
            LOG.debug(f"Error while handling heartbeat timeout for server {ip}: {e}")

    async def inject_daemon(self, server: dict) -> bool:
        """Inject heartbeat daemon to target server"""
        ip = server["device"]["ip"]
        username = server["device"].get("username", "root")
        password = server["device"].get("password", "")
        server_id = server["id"]

        try:
            return await self.ssh_inject_daemon(ip, username, password, server_id)
        except Exception as e:
            LOG.debug(f"Daemon injection via SSH failed for server {server_id} (ip={ip}): {e}")
            return False

    async def ssh_inject_daemon(
        self,
        ip: str,
        username: str,
        password: str,
        server_id: str
    ) -> bool:
        """Inject daemon as systemd service through SSH"""

        try:
            # 检查是否已运行
            try:
                status = await ssh_execute_async(
                    ip, 
                    "systemctl is-active server-daemon.service 2>/dev/null", 
                    username, password, 
                    False
                )
                if status.strip() == "active":
                    return True
            except Exception:
                pass

            # 安装守护进程
            service_content = self.generate_systemd_service(server_id)

            await common_utils.ensure_packages_installed(ip, username, password, ["curl"])

            daemon_url = f"{settings.file_server}/daemon/server_daemon.sh"
            cmd = f"""
mkdir -p /opt/server_daemon
curl -fsSkL {daemon_url} -o /opt/server_daemon/server_daemon.sh
chmod +x /opt/server_daemon/server_daemon.sh

cat > /etc/systemd/system/server-daemon.service << 'EOF'
{service_content}
EOF

systemctl daemon-reload
systemctl enable --now server-daemon.service
"""

            await ssh_execute_async(ip, cmd, username, password, False)
            return True

        except Exception as e:
            LOG.debug(f"Daemon injection failed for {ip}: {e}")
            return False