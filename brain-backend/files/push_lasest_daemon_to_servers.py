# Copyright (C) 2021 - 2025, Shanghai Yunsilicon Technology Co., Ltd.
# All rights reserved.

import logging

from brain.json_db import SQLiteDocumentDB
from brain.config import settings
from brain.utils import common_utils
from brain.utils.ssh_client import ssh_execute_async
from brain.heartbeat_monitor import HeartbeatMonitor as RealHeartbeatMonitor

db = SQLiteDocumentDB()
SERVER_COLLECTION = "servers"
LOG = logging.getLogger(__name__)


class HeartbeatMonitor:

    async def start_monitoring(self):
        """Start heartbeat monitoring loop"""
        print("Heartbeat monitor started")
        try:
            await self.check_all_servers()
        except Exception as e:
            print(f"Heartbeat monitor loop error: {e}")

    async def check_all_servers(self):
        """Check heartbeat status for all servers"""
        servers = db.find(SERVER_COLLECTION)
        for server in servers:
            await self.handle_heartbeat_timeout(server)

    async def handle_heartbeat_timeout(self, server: dict):
        """Handle heartbeat timeout for a server"""
        ip = server["device"]["ip"]

        try:
            success = await self.inject_daemon(server)

            if success:
                pass
                # print(f"Daemon injection succeeded for server {ip}")
            else:
                print(f"Daemon injection failed for server {ip}")

        except Exception as e:
            print(f"Error while handling heartbeat timeout for server {ip}: {e}")

    async def inject_daemon(self, server: dict) -> bool:
        """Inject heartbeat daemon to target server"""
        ip = server["device"]["ip"]
        username = server["device"].get("username", "root")
        password = server["device"].get("password", "")
        server_id = server["id"]

        try:
            return await self.ssh_inject_daemon(ip, username, password, server_id)
        except Exception as e:
            # print(f"Daemon injection via SSH failed for server {server_id} (ip={ip}): {e}")
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
            # 安装守护进程
            real = RealHeartbeatMonitor()
            service_content = real.generate_systemd_service(server_id)

            await common_utils.ensure_packages_installed(ip, username, password, ["curl"])

            daemon_url = f"{settings.file_server}/daemon/server_daemon.sh"
            cmd = f"""
systemctl stop server-daemon
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
            # print(f"Daemon injection failed for {ip}: {e}")
            return False