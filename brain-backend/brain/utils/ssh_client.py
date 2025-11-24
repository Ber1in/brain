# Copyright (C) 2021 - 2025, Shanghai Yunsilicon Technology Co., Ltd.
# All rights reserved.

import asyncio
import concurrent.futures
import paramiko
import logging
from paramiko import ssh_exception

from fastapi import HTTPException

LOG = logging.getLogger(__name__)


async def ssh_execute_async(host: str, command: str, user: str, pwd: str) -> str:
    """Execute a command on remote host via SSH asynchronously"""
    loop = asyncio.get_event_loop()
    try:
        with concurrent.futures.ThreadPoolExecutor() as pool:
            result = await loop.run_in_executor(
                pool, 
                lambda: ssh_execute(host, command, user, pwd)
            )
            return result
    except HTTPException:
        raise
    except Exception as e:
        LOG.error(f"Async SSH execution failed on {host}: {e}")
        raise HTTPException(status_code=500, detail=f"SSH execution failed on {host}: {e}")


def ssh_execute(host: str, command: str, user: str, pwd: str) -> str:
    """Execute a command on remote host via SSH"""
    LOG.debug(f"Executing SSH command on {host}: {command}")
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(host, username=user, password=pwd, timeout=6)
        stdin, stdout, stderr = ssh.exec_command(command)
        out = stdout.read().decode()
        err = stderr.read().decode()
        ssh.close()
        if err:
            LOG.warning(f"Command error on {host}: {err.strip()}")
        LOG.debug(f"SSH command completed on {host}")
        return out.strip()
    except (ssh_exception.NoValidConnectionsError, TimeoutError) as e:
        LOG.error(e)
        raise HTTPException(status_code=503, detail=f"{e}")
    except ssh_exception.AuthenticationException as e:
        LOG.error(e)
        raise HTTPException(status_code=509, detail=f"{e}")
    except Exception as e:
        LOG.error(f"SSH execution failed on {host}: {e}")
        raise HTTPException(status_code=500, detail=f"SSH execution failed on {host}: {e}")