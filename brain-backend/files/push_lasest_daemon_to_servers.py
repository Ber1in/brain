# Copyright (C) 2021 - 2025, Shanghai Yunsilicon Technology Co., Ltd.
# All rights reserved.

from brain.heartbeat_monitor import HeartbeatMonitor as RealHeartbeatMonitor
from brain.utils.ssh_client import ssh_execute_async
from brain.utils import common_utils
from brain.config import settings
from brain.json_db import SQLiteDocumentDB
import argparse
import asyncio
import logging
import sys
import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


db = SQLiteDocumentDB()
SERVER_COLLECTION = "servers"
LOG = logging.getLogger(__name__)


class HeartbeatMonitor:

    async def start_monitoring(self, server_ips: list = None):
        """Start heartbeat monitoring loop"""
        print("Heartbeat monitor started")
        try:
            if server_ips:
                # Check specific servers
                for ip in server_ips:
                    try:
                        server = self.get_server_by_ip(ip)
                    except Exception:
                        print(f"Server with IP {ip} not found in the database.")
                    await self.handle_heartbeat_timeout(server)
                        
            else:
                # Check all servers
                servers = db.find(SERVER_COLLECTION)
                for server in servers:
                    await self.handle_heartbeat_timeout(server)
        except Exception as e:
            print(f"Heartbeat monitor loop error: {e}")

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

    def get_server_by_ip(self, server_ip: str):
        """Get server information by IP"""
        return db.find_one(SERVER_COLLECTION, {"json_extract(device, '$.ip')": server_ip})


def parse_arguments():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(description="Heartbeat monitoring tool.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--server-ips",
        type=str,
        help="Comma-separated list of server IPs to update"
    )
    group.add_argument(
        "--all",
        action="store_true",
        help="Update all servers"
    )

    return parser.parse_args()


async def main():
    args = parse_arguments()

    monitor = HeartbeatMonitor()

    if args.all:
        await monitor.start_monitoring()
    elif args.server_ips:
        server_ips = args.server_ips.split(',')
        await monitor.start_monitoring(server_ips)

if __name__ == "__main__":
    asyncio.run(main())
