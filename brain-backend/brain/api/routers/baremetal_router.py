# Copyright (C) 2021 - 2025, Shanghai Yunsilicon Technology Co., Ltd.
# All rights reserved.

import re
import paramiko
import subprocess
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List
import logging
import uuid

from brain.json_db import JSONDocumentDB
from brain.auth import authenticate_user
from brain.api.schemas import bare_metal_schemas

router = APIRouter(dependencies=[Depends(authenticate_user)])
LOG = logging.getLogger(__name__)
db = JSONDocumentDB()

# Collection name
BARE_METAL_SERVER_COLLECTION = "bare_metals"
BMC_USER = "ipmiadmin"
BMC_PASS = "ymxl@2022"


@router.post("/bare-metals", response_model=bare_metal_schemas.BareMetalServer,
             status_code=status.HTTP_201_CREATED)
async def create_bare_metal_server(server_data: bare_metal_schemas.BareMetalServerCreate):
    """
    Create a new bare metal
    """
    LOG.info(f"Received request to create bare metal server: {server_data.name}")
    try:
        # Check if name already exists
        existing_server = db.find(BARE_METAL_SERVER_COLLECTION, {"name": server_data.name})
        if existing_server:
            LOG.warning(f"Server name {server_data.name} already exists")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Server with this name already exists"
            )

        # Check if IP address already exists
        existing_ip = db.find(BARE_METAL_SERVER_COLLECTION, {"host_ip": server_data.host_ip})
        if existing_ip:
            LOG.warning(f"Server IP {server_data.host_ip} already exists")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Server with this IP address already exists"
            )

        # Generate unique ID and create server document
        server_id = str(uuid.uuid4())
        server_dict = {
            "id": server_id,
            **server_data.dict()
        }

        LOG.info(f"Creating bare metal server {server_id} with name {server_data.name}")
        # Insert new server
        db.insert(BARE_METAL_SERVER_COLLECTION, server_dict)
        LOG.info(f"Successfully created bare metal server {server_id}")

        # Return the created server information
        return server_dict

    except HTTPException:
        raise
    except Exception as e:
        LOG.error(f"Failed to create bare metal {server_data.name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create bare metal: {e}"
        )


@router.get("/bare-metals", response_model=List[bare_metal_schemas.BareMetalServer])
async def get_all_bare_metals():
    """
    Get all bare metals list
    """
    LOG.info("Received request to get all bare metal servers")
    try:
        servers = db.find(BARE_METAL_SERVER_COLLECTION, {})
        LOG.info(f"Retrieved {len(servers)} bare metal servers from database")
        return servers
    except Exception as e:
        LOG.error(f"Failed to get bare metals: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get bare metals"
        )


@router.get("/bare-metals/{server_id}", response_model=bare_metal_schemas.BareMetalServer)
async def get_bare_metal_server(server_id: str):
    """
    Get specific bare metal by ID
    """
    LOG.info(f"Received request to get bare metal server {server_id}")
    try:
        server = db.find_one(BARE_METAL_SERVER_COLLECTION, {"id": server_id})
        if not server:
            LOG.warning(f"Bare metal server {server_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="bare metal not found"
            )

        LOG.info(f"Successfully retrieved bare metal server {server_id}")
        return server
    except HTTPException:
        raise
    except Exception as e:
        LOG.error(f"Failed to get bare metal {server_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get bare metal"
        )


@router.put("/bare-metals/{server_id}", response_model=bare_metal_schemas.BareMetalServer)
async def update_bare_metal_server(
        server_id: str, update_data: bare_metal_schemas.BareMetalServerUpdate):
    """
    Update bare metal information by ID
    """
    LOG.info(f"Received request to update bare metal server {server_id}")
    try:
        # Check if server exists
        existing_server = db.find_one(BARE_METAL_SERVER_COLLECTION, {"id": server_id})
        if not existing_server:
            LOG.warning(f"Bare metal server {server_id} not found for update")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="bare metal not found"
            )

        # If updating name, check if name conflicts with other servers
        if update_data.name and update_data.name != existing_server.get("name"):
            same_name_servers = db.find(BARE_METAL_SERVER_COLLECTION, {"name": update_data.name})
            if same_name_servers:
                LOG.warning(f"Name {update_data.name} conflicts with existing server")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Another server with this name already exists"
                )

        # If updating IP address, check if IP conflicts with other servers
        if update_data.host_ip and update_data.host_ip != existing_server.get("host_ip"):
            same_ip_servers = db.find(BARE_METAL_SERVER_COLLECTION,
                                      {"host_ip": update_data.host_ip})
            if same_ip_servers:
                LOG.warning(f"IP {update_data.host_ip} conflicts with existing server")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Another server with this IP address already exists"
                )

        # Update server information (excluding ID field)
        update_dict = {k: v for k, v in update_data.dict(
            exclude_unset=True).items() if v is not None}
        if update_dict:
            LOG.info(f"Updating server {server_id} with fields: {list(update_dict.keys())}")
            updated_count = db.update(BARE_METAL_SERVER_COLLECTION, {"id": server_id}, update_dict)
            if updated_count == 0:
                LOG.error(f"Failed to update server {server_id} in database")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="bare metal not found"
                )
            LOG.info(f"Successfully updated server {server_id} in database")
        else:
            LOG.info(f"No fields to update for server {server_id}")

        # Return updated server information
        updated_server = db.find_one(BARE_METAL_SERVER_COLLECTION, {"id": server_id})
        LOG.info(f"Successfully completed update for server {server_id}")
        return updated_server

    except HTTPException:
        raise
    except Exception as e:
        LOG.error(f"Failed to update bare metal {server_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update bare metal"
        )


@router.delete("/bare-metals/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bare_metal_server(server_id: str):
    """
    Delete bare metal by ID
    """
    LOG.info(f"Received request to delete bare metal server {server_id}")
    try:
        # Check if server exists
        existing_servers = db.find(BARE_METAL_SERVER_COLLECTION, {"id": server_id})
        if not existing_servers:
            LOG.warning(f"Bare metal server {server_id} not found for deletion")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="bare metal not found"
            )

        server_name = existing_servers[0].get("name", "unknown")
        LOG.info(f"Deleting bare metal server {server_id} ({server_name})")
        # Delete server
        deleted_count = db.delete(BARE_METAL_SERVER_COLLECTION, {"id": server_id})
        if deleted_count == 0:
            LOG.error(f"Failed to delete server {server_id} from database")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="bare metal not found"
            )

        LOG.info(f"Successfully deleted bare metal server {server_id}")
    except HTTPException:
        raise
    except Exception as e:
        LOG.error(f"Failed to delete bare metal {server_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete bare metal"
        )


def ssh_execute(host: str, command: str, user: str, pwd: str) -> str:
    """Execute a command on remote host via SSH"""
    LOG.debug(f"Executing SSH command on {host}: {command}")
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(host, username=user, password=pwd, timeout=10)
        stdin, stdout, stderr = ssh.exec_command(command)
        out = stdout.read().decode()
        err = stderr.read().decode()
        ssh.close()
        if err:
            LOG.warning(f"Command error on {host}: {err.strip()}")
        LOG.debug(f"SSH command completed on {host}")
        return out.strip()
    except Exception as e:
        LOG.error(f"SSH execution failed on {host}: {e}")
        raise HTTPException(status_code=500, detail=f"SSH execution failed on {host}: {e}")


@router.get("/bare-metals/{server_id}/boot-entries",
            response_model=bare_metal_schemas.BootEntriesResponse)
async def get_boot_entries(
    server_id: str, 
    use_saved: bool = Query(False),
    user: str = Query(None),
    pwd: str = Query(None)
):
    """
    Get all boot entries (name + parent disk) and current boot
    """
    LOG.info(f"Received request to get boot entries for server {server_id}, use_saved: {use_saved}")
    server = db.find_one(BARE_METAL_SERVER_COLLECTION, {"id": server_id})
    if not server:
        LOG.warning(f"Server {server_id} not found for boot entries query")
        raise HTTPException(status_code=404, detail="bare metal not found")

    host_ip = server.get("host_ip")
    if not host_ip:
        LOG.error(f"Server {server_id} has no host_ip configured")
        raise HTTPException(status_code=400, detail="host_ip not configured for this server")

    if use_saved:
        credentials_user = server.get("os_user")
        credentials_pwd = server.get("os_password")
        if not credentials_user or not credentials_pwd:
            raise HTTPException(
                status_code=400, detail="No saved OS credentials found for this server")
    else:
        if not user or not pwd:
            raise HTTPException(
                status_code=400, 
                detail="Username and password are required when use_saved is False")
        credentials_user = user
        credentials_pwd = pwd

    LOG.info(f"Retrieving boot entries from server {server_id} ({host_ip})")
    efiboot_output = ssh_execute(host_ip, "efibootmgr -v",
                                 credentials_user, credentials_pwd).splitlines()
    lsblk_output = ssh_execute(host_ip, "lsblk -no PARTUUID,PKNAME",
                               credentials_user, credentials_pwd).splitlines()

    uuid_to_disk = {}
    for line in lsblk_output:
        parts = line.strip().split()
        if len(parts) == 2:
            uuid, disk = parts
            uuid_to_disk[uuid.lower()] = disk

    entries = {}
    current_boot = None
    next_boot = None

    for line in efiboot_output:
        line = line.strip()
        if line.startswith("BootCurrent"):
            current_boot = line.split(":")[1].strip()
        elif line.startswith("BootNext"):
            next_boot = line.split(":")[1].strip()
        elif line.startswith("Boot") and "*" in line:
            boot_num, rest = line.split("*", 1)
            boot_num = boot_num.strip().replace("Boot", "")
            name = rest.strip().split("\t")[0]
            if not name.startswith("UEFI: PXE") and "EFI Shell" not in name:
                m = re.search(r"GPT,([0-9a-fA-F-]+)", line)
                disk = ""
                if m:
                    uuid = m.group(1).lower()
                    disk = uuid_to_disk.get(uuid, "")
                entries[boot_num] = f"{name} ({disk})" if disk else name

    LOG.info(f"Found {len(entries)} boot entries for server {server_id}")
    return {
        "entries": entries,
        "current": current_boot,
        "next": next_boot
    }


@router.post("/bare-metals/{server_id}/set-boot")
async def set_boot_entry(
    server_id: str, 
    boot_id: str = Query(...),
    use_saved: bool = Query(False),
    set_default: bool = Query(False),
    user: str = Query(None),
    pwd: str = Query(None)
):
    """
    Set boot entry for bare metal server
    """
    LOG.info(
        f"Received request to set boot entry {boot_id} for server {server_id}, "
        f"use_saved: {use_saved}, set_default: {set_default}"
    )

    server = db.find_one(BARE_METAL_SERVER_COLLECTION, {"id": server_id})
    if not server:
        LOG.warning(f"Server {server_id} not found for set boot operation")
        raise HTTPException(status_code=404, detail="bare metal not found")

    host_ip = server.get("host_ip")
    if not host_ip:
        LOG.error(f"Server {server_id} has no host_ip configured")
        raise HTTPException(status_code=400, detail="host_ip not configured for this server")

    if use_saved:
        credentials_user = server.get("os_user")
        credentials_pwd = server.get("os_password")
        if not credentials_user or not credentials_pwd:
            raise HTTPException(
                status_code=400, detail="No saved OS credentials found for this server")
    else:
        if not user or not pwd:
            raise HTTPException(
                status_code=400, 
                detail="Username and password are required when use_saved is False")
        credentials_user = user
        credentials_pwd = pwd

    LOG.info(f"Setting next boot entry {boot_id} on server {server_id} ({host_ip})")
    ssh_execute(host_ip, f"efibootmgr -n {boot_id}", credentials_user, credentials_pwd)

    if set_default:
        LOG.info(f"Setting default boot entry {boot_id} on server {server_id} ({host_ip})")
        out = ssh_execute(host_ip, "efibootmgr | grep BootOrder", credentials_user, credentials_pwd)
        boot_order_line = out.strip().split(":")[-1].strip()
        boot_list = boot_order_line.split(",")
        if boot_id in boot_list:
            boot_list.remove(boot_id)
        new_order = ",".join([boot_id] + boot_list)
        ssh_execute(host_ip, f"efibootmgr -o {new_order}", credentials_user, credentials_pwd)
        LOG.info(f"Default boot entry set to {boot_id} with order {new_order}")

    return {"message": (f"BootNext set to {boot_id} on {host_ip}"
                        f"{' (default updated)' if set_default else ''}")}


def get_bmc_ip(host_ip: str) -> str:
    """Convert host_ip like 10.0.3.x to BMC ip 10.0.2.x"""
    parts = host_ip.split(".")
    if len(parts) != 4:
        raise ValueError(f"Invalid host_ip format: {host_ip}")
    parts[2] = "2"  # replace the third octet
    bmc_ip = ".".join(parts)
    LOG.debug(f"Converted host_ip {host_ip} to BMC IP {bmc_ip}")
    return bmc_ip


def ipmi_power_action(bmcip: str, action: str):
    """Execute IPMI power action via ipmitool command"""
    LOG.info(f"Executing IPMI {action} on BMC {bmcip}")

    if action not in ("cycle", "reset"):
        raise HTTPException(status_code=400, detail=f"Unsupported IPMI action: {action}")

    # ipmitool chassis power 命令参数
    cmd = [
        "ipmitool",
        "-I", "lanplus",
        "-H", bmcip,
        "-U", BMC_USER,
        "-P", BMC_PASS,
        "chassis",
        "power",
        action
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            LOG.error(f"IPMI {action} failed on BMC {bmcip}: {result.stderr.strip()}")
            raise HTTPException(
                status_code=500,
                detail=f"IPMI {action} failed: {result.stderr.strip()}"
            )
        LOG.info(f"Successfully executed IPMI {action} on BMC {bmcip}: {result.stdout.strip()}")
    except Exception as e:
        LOG.error(f"IPMI {action} execution error on BMC {bmcip}: {e}")
        raise HTTPException(status_code=500, detail=f"IPMI {action} execution error: {e}")


@router.post("/bare-metals/{server_id}/power-cycle")
async def power_cycle_server(server_id: str):
    """
    Power cycle bare metal server via BMC
    """
    LOG.info(f"Received request to power cycle server {server_id}")
    server = db.find_one(BARE_METAL_SERVER_COLLECTION, {"id": server_id})
    if not server:
        LOG.warning(f"Server {server_id} not found for power cycle")
        raise HTTPException(status_code=404, detail="bare metal not found")

    host_ip = server.get("host_ip")
    if not host_ip:
        LOG.error(f"Server {server_id} has no host_ip configured")
        raise HTTPException(status_code=400, detail="host_ip not configured for this server")

    bmcip = get_bmc_ip(host_ip)
    LOG.info(f"Power cycling server {server_id} via BMC {bmcip}")
    ipmi_power_action(bmcip, "cycle")

    LOG.info(f"Successfully completed power cycle for server {server_id}")
    return {"message": f"Server {server_id} power cycled via BMC {bmcip}"}


@router.post("/bare-metals/{server_id}/power-reset")
async def power_reset_server(server_id: str):
    """
    Warm reset bare metal server via BMC
    """
    LOG.info(f"Received request to power reset server {server_id}")
    server = db.find_one(BARE_METAL_SERVER_COLLECTION, {"id": server_id})
    if not server:
        LOG.warning(f"Server {server_id} not found for power reset")
        raise HTTPException(status_code=404, detail="bare metal not found")

    host_ip = server.get("host_ip")
    if not host_ip:
        LOG.error(f"Server {server_id} has no host_ip configured")
        raise HTTPException(status_code=400, detail="host_ip not configured for this server")

    bmcip = get_bmc_ip(host_ip)
    LOG.info(f"Power resetting server {server_id} via BMC {bmcip}")
    ipmi_power_action(bmcip, "reset")

    LOG.info(f"Successfully completed power reset for server {server_id}")
    return {"message": f"Server {server_id} warm rebooted via BMC {bmcip}"}


@router.post("/bare-metals/{server_id}/verify-credentials")
async def verify_credentials(
    server_id: str,
    use_saved: bool = Query(False),
    user: str = Query(None),
    pwd: str = Query(None)
):
    """
    验证服务器操作系统凭据是否有效
    """
    LOG.info(f"Verifying OS credentials for server {server_id}, use_saved: {use_saved}")
    server = db.find_one(BARE_METAL_SERVER_COLLECTION, {"id": server_id})
    if not server:
        raise HTTPException(status_code=404, detail="bare metal not found")

    host_ip = server.get("host_ip")
    if not host_ip:
        raise HTTPException(status_code=400, detail="host_ip not configured for this server")

    # 确定使用的凭据
    if use_saved:
        credentials_user = server.get("os_user")
        credentials_pwd = server.get("os_password")
        if not credentials_user or not credentials_pwd:
            return {
                "valid": False, 
                "has_saved_credentials": False,
                "message": "No saved OS credentials found"
            }
    else:
        if not user or not pwd:
            raise HTTPException(
                status_code=400,
                detail="Username and password are required when use_saved is False")
        credentials_user = user
        credentials_pwd = pwd

    try:
        # 执行一个简单的命令来验证凭据
        result = ssh_execute(host_ip, "echo 'connection_test'", credentials_user, credentials_pwd)
        if "connection_test" in result:
            return {
                "valid": True, 
                "has_saved_credentials": use_saved or bool(server.get("os_user")),
                "message": "OS credentials are valid"
            }
        else:
            return {
                "valid": False,
                "has_saved_credentials": use_saved or bool(server.get("os_user")),
                "message": "Invalid response from server"
            }
    except Exception as e:
        LOG.error(f"OS credential verification failed for server {server_id}: {str(e)}")
        return {
            "valid": False,
            "has_saved_credentials": use_saved or bool(server.get("os_user")),
            "message": f"SSH connection failed: {str(e)}"
        }


@router.put("/bare-metals/{server_id}/credentials")
async def update_server_credentials(
    server_id: str,
    credentials: bare_metal_schemas.ServerCredentials
):
    """
    更新服务器操作系统凭据
    """
    LOG.info(f"Updating OS credentials for server {server_id}")
    server = db.find_one(BARE_METAL_SERVER_COLLECTION, {"id": server_id})
    if not server:
        raise HTTPException(status_code=404, detail="bare metal not found")

    update_data = {
        "os_user": credentials.user,
        "os_password": credentials.pwd
    }

    db.update_one(BARE_METAL_SERVER_COLLECTION, {"id": server_id}, update_data)

    LOG.info(f"Successfully updated OS credentials for server {server_id}")
    return {"message": "OS credentials updated successfully"}