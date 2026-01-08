# Copyright (C) 2021 - 2025, Shanghai Yunsilicon Technology Co., Ltd.
# All rights reserved.

import asyncio
import concurrent.futures
import contextvars
import paramiko
import logging
from paramiko import ssh_exception
from stat import S_ISDIR, S_ISLNK
import asyncssh

from fastapi import HTTPException

LOG = logging.getLogger(__name__)

IGNORE_DIRS = [".", ".."]


async def ssh_execute_async(host: str, command: str, user: str, pwd: str, check=True) -> str:
    """Execute a command on remote host via SSH asynchronously"""
    loop = asyncio.get_event_loop()
    ctx = contextvars.copy_context()

    try:
        with concurrent.futures.ThreadPoolExecutor() as pool:
            result = await loop.run_in_executor(
                pool,
                lambda: ctx.run(ssh_execute, host, command, user, pwd, check)
            )
            return result
    except HTTPException:
        raise
    except Exception as e:
        LOG.error(f"Async SSH execution {command} failed on {host}: {e}")
        raise HTTPException(
            status_code=500, detail=f"SSH execution {command} failed on {host}: {e}")


def ssh_execute(host: str, command: str, user: str, pwd: str, check=True) -> str:
    """Execute a command on remote host via SSH"""
    LOG.debug(f"Executing SSH command on {host}: {command}")
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(host, username=user, password=pwd, timeout=6)
        stdin, stdout, stderr = ssh.exec_command(command)

        out = stdout.read().decode('latin-1')
        err = stderr.read().decode('latin-1')

        exit_code = stdout.channel.recv_exit_status()
        ssh.close()

        if check and err:
            LOG.error(f"Command {command} error on {host}: \n"
                      f"stdout: {out.strip()} \nstderr: {err.strip()}")
        if check and exit_code != 0:
            LOG.debug(f"Command {command} failed on {host} (exit {exit_code}): {out.strip()}")
            raise HTTPException(
                status_code=500,
                detail=f"SSH command failed: \nstdout: {out.strip()} \nstderr: {err.strip()}")

        LOG.debug(f"SSH command {command} completed on {host}")
        return out.strip()
    except (ssh_exception.NoValidConnectionsError, TimeoutError) as e:
        LOG.error(e)
        raise HTTPException(status_code=503, detail=f"{e}")
    except ssh_exception.AuthenticationException as e:
        LOG.error(e)
        raise HTTPException(status_code=509, detail=f"{e}")
    except Exception as e:
        LOG.error(f"SSH execution {command} failed on {host}: {e}")
        raise HTTPException(
            status_code=500, detail=f"SSH execution {command} failed on {host}: {e}")


class AsyncRemoteFS:
    def __init__(self, host, username, password=None, port=22):
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self._conn = None
        self._sftp = None

    async def _connect(self):
        if self._conn:
            return

        self._conn = await asyncssh.connect(
            self.host,
            port=self.port,
            username=self.username,
            password=self.password,
            known_hosts=None,
        )
        self._sftp = await self._conn.start_sftp_client()

    async def _is_connected(self):
        if not self._conn:
            return False

        try:
            await self._conn.run("echo ok", check=True, timeout=5)
            return True
        except Exception:
            return False

    async def _ensure_connected(self):
        if not await self._is_connected():
            await self._close()
            await self._connect()

    async def listdir(self, remote_path):
        """Return items under remote_path (with type: file/directory)."""
        await self._ensure_connected()

        items = []
        async for entry in self._sftp.scandir(remote_path):
            if entry.filename in IGNORE_DIRS:
                continue

            # Check if it's a symlink
            if S_ISLNK(entry.attrs.permissions):
                # Follow the symlink to check if it points to a directory
                target_path = await self._sftp.realpath(remote_path + '/' + entry.filename)
                try:
                    target_stat = await self._sftp.stat(target_path)
                    if S_ISDIR(target_stat.permissions):
                        items.append({
                            "name": entry.filename,
                            "type": "directory"
                        })
                    else:
                        items.append({
                            "name": entry.filename,
                            "type": "file"
                        })
                except Exception:
                    items.append({
                        "name": entry.filename,
                        "type": "file"
                    })
            else:
                items.append({
                    "name": entry.filename,
                    "type": "directory" if S_ISDIR(entry.attrs.permissions) else "file"
                })
        return items

    async def download(self, remote_path, local_path):
        """Download remote file to local."""
        await self._ensure_connected()
        await self._sftp.get(remote_path, local_path)

    async def _close(self):
        if self._sftp:
            try:
                self._sftp.exit()
            except Exception:
                pass
            self._sftp = None

        if self._conn:
            try:
                self._conn.close()
                await self._conn.wait_closed()
            except Exception:
                pass
            self._conn = None

    async def __aenter__(self):
        await self._connect()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self._close()