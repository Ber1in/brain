# Copyright (C) 2021 - 2025, Shanghai Yunsilicon Technology Co., Ltd.
# All rights reserved.

import asyncio
from datetime import datetime
import re
from typing import List, Union
from uuid import uuid4
from fastapi import APIRouter, Depends, status, HTTPException, Query
import logging

from brain.auth import authenticate_user
from brain.api.v2.schemas import common_schemas, server_schemas
from brain.json_db import SQLiteDocumentDB
from brain.utils.ssh_client import ssh_execute_async
from brain.utils import common_utils, task_scheduler
from brain.utils.task_scheduler import task_scheduler as scheduler


LOG = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(authenticate_user)])
BMC_USER = "ipmiadmin"
BMC_PASS = "ymxl@2022"
db = SQLiteDocumentDB()
SERVER_COLLECTION = "servers"
ALIAS_NAMES = {
    "metaConnect-400S 400GbE, Single-port QSFP112, PCIe 5.0 x16": "MC400S",
    "metaScale-200 100GbE OCP3.0, Dual-port DSFP, Multi Host, PCIe 4.0 x16": "MS200-OCP",
    "metaScale-200S 200GbE Single-Port QSFP56, PCIe 4.0 x16": "MS200s",
    "MS200s-03XX": "MS200s"
}


@router.post("/servers", response_model=server_schemas.ServerDetailResponse)
async def create_device(data: server_schemas.ServerRequest):
    LOG.info(f"Creating server, IP: {data.device.ip}, hostname: {data.bmc.hostname}")

    exist = db.find(SERVER_COLLECTION,
                    {"json_extract(device, '$.ip')": str(data.device.ip)})
    if exist:
        LOG.warning(f"Server already exists, IP: {data.device.ip}")
        raise HTTPException(
            status_code=400,
            detail=f"Server with IP {data.device.ip} already exists"
        )

    exist = db.find(SERVER_COLLECTION,
                    {"json_extract(bmc, '$.hostname')": data.bmc.hostname})
    if exist:
        LOG.warning(f"Server already exists, name: {data.bmc.hostname}")
        raise HTTPException(
            status_code=400,
            detail=f"Server with name {data.bmc.hostname} already exists"
        )

    device, nics = await common_utils.update_automatic_async(
        str(data.device.ip), data.device.username, data.device.password
    )
    LOG.info(f"Auto discovery completed, SN: {device['sn']}, NICs: {len(nics)}")

    await common_utils.ensure_packages_installed(
        str(data.device.ip), data.device.username, data.device.password, ["ipmitool"])
    channels = [1, 2, 0]

    for channel in channels:
        impi_info = await ssh_execute_async(
            str(data.device.ip), 
            f"ipmitool lan print {channel}",
            data.device.username, 
            data.device.password,
            check=False
        )

        match = re.search(r"IP Address\s*:\s*([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)", impi_info)

        if match:
            bmc_ip = match.group(1)
            break
    else:
        raise HTTPException(500, detail="Unable to find IMPI address") 

    device.update({
        "ip": str(data.device.ip),
        "username": data.device.username,
        "password": data.device.password
    })
    result = {
        "bmc": {
            "ip": bmc_ip,
            "hostname": data.bmc.hostname},
        "device": device,
        "nics": nics,
        "tags": data.tags,
        "notes": data.notes if data.notes is not None else "",
        "user": "",
        "time": 0,
        "start": "",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "updated_at": "",
        "id": str(uuid4()),
        "recipients": [],
        "task_id": "",
    }

    db.insert(SERVER_COLLECTION, result)
    LOG.info(f"Server created, ID: {result['id']}")

    try:
        await task_scheduler.init_warning(
            str(data.device.ip), data.device.username, data.device.password)
    except Exception:
        LOG.warning("Failed to initialize the server usage warning message.")

    return result


@router.delete("/servers/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_device(device_id: str):
    LOG.info(f"Deleting Server, ID: {device_id}")
    try:
        server = db.find_one(SERVER_COLLECTION, {"id": device_id})
    except Exception as e:
        LOG.warning(f"Server not found, {e}")
        raise HTTPException(status_code=404, detail=f"Server not found, {e}")

    deleted = db.delete(SERVER_COLLECTION, {"id": device_id})
    if not deleted:
        LOG.warning(f"Server not found, ID: {device_id}")
    else:
        LOG.info(f"Server deleted, ID: {device_id}")

    try:
        clean_command = "sed -i '/# WARNING_MESSAGE_START/,/# WARNING_MESSAGE_END/d' /etc/profile"
        await ssh_execute_async(server["device"]["ip"], clean_command, server["device"]
                                ["username"], server["device"]["password"])
        warn_task_id = f"device_warn_{server['device']['ip'].replace('.', '_')}"
        success = await scheduler.cancel_task(warn_task_id)
        task_id = f"device_cleanup_{server['device']['ip'].replace('.', '_')}"
        success = await scheduler.cancel_task(task_id)

        if success:
            LOG.info(f"Successfully cancelled auto cleanup for device {device_id}")
        else:
            LOG.info(f"No auto cleanup task found for device {device_id}")

    except Exception:
        LOG.warning("Failed to initialize the server usage warning message.")


@router.get("/servers", response_model=list[server_schemas.ServerDetailResponse])
async def get_all_devices():
    LOG.info(f"Fetching all servers.")
    devices = db.find(SERVER_COLLECTION, {})
    for i in devices:
        if i["time"]:
            now = datetime.now().timestamp()
            start = i.get("start")
            passed = int(now - start)
            remaining = i["time"] - passed
            i["time"] = max(remaining, 0)
    LOG.info(f"Total servers fetched: {len(devices)}")
    return devices


@router.get("/servers/{device_id}", response_model=server_schemas.ServerDetailResponse)
async def get_device(device_id: str):
    LOG.info(f"Fetching device, ID: {device_id}")
    try:
        server = db.find_one(SERVER_COLLECTION, {"id": device_id})
        if server["time"]:
            now = datetime.now().timestamp()
            start = server.get("start")
            passed = int(now - start)
            remaining = server["time"] - passed
            server["time"] = max(remaining, 0)
    except Exception as e:
        LOG.warning(f"Device not found, {e}")
        raise HTTPException(status_code=404, detail=f"Device not found, {e}")

    LOG.info(f"Device fetched: ip={server['device']['ip']}")
    return server


@router.put("/servers/{device_id}", response_model=server_schemas.ServerDetailResponse)
async def update_device(
    device_id: str,
    data: server_schemas.ServerUpdateRequest,
    user=Depends(authenticate_user)
):

    try:
        server = db.find_one(SERVER_COLLECTION, {"id": device_id})
    except Exception:
        LOG.warning(f"Device not found, ID: {device_id}")
        raise HTTPException(status_code=404, detail="Device not found")

    LOG.info(f"Updating device, server: {server['device']['ip']}, auto: {data.auto}, user: {user}")
    if data.auto:
        LOG.info(f"Automatic updating device: {server['device']['ip']}")

        device, nics = await common_utils.update_automatic_async(
            server["device"]["ip"],
            server["device"].get("username", ""),
            server["device"].get("password", "")
        )
        server["device"].update(device)
        server["nics"] = nics

    else:
        LOG.info(f"Manual updating device: {server['device']['ip']}")

        if data.device and data.device.password:
            server["device"]["password"] = data.device.password

        if data.bmc and data.bmc.hostname:
            server["bmc"]["hostname"] = data.bmc.hostname

        if data.tags is not None:
            server["tags"] = data.tags

        if data.notes is not None:
            server["notes"] = data.notes

    server["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    db.update(SERVER_COLLECTION, {"id": device_id}, server)

    LOG.info(f"Device updated, server: {server['device']['ip']}, user: {user}, time: {server.get('time', 0)}")
    return server


@router.patch("/servers/{server_id}/occupy", response_model=server_schemas.ServerDetailResponse)
async def occupy_server(
    server_id: str, 
    data: server_schemas.ServerOccupyRequest,
    user: str = Depends(authenticate_user)
) -> dict:
    """
    Occupy or release a server.

    If `data.time > 0`, mark the server as occupied by the current user for the specified time,
    schedule warnings and auto-cleanup tasks.  
    If `data.time <= 0`, release the server and cancel any scheduled tasks.

    Args:
        server_id: The ID of the server to occupy/release.
        data: ServerOccupyRequest containing the occupy time in seconds.
        user: The authenticated username (injected by Depends).

    Returns:
        The updated server record as a dict.
    """

    try:
        server = db.find_one(SERVER_COLLECTION, {"id": server_id})
    except Exception:
        LOG.warning(f"Device not found, ID: {server_id}")
        raise HTTPException(status_code=404, detail="Device not found")

    server["time"] = data.time
    server["start"] = datetime.now().timestamp()
    ip: str = server["device"]["ip"]
    ssh_user = server["device"].get("username", "")
    ssh_pass = server["device"].get("password", "")
    time = int(data.time)

    LOG.info(f"occupy_server called: ip={ip}, user={user}, time={data.time}")
    if time > 0:
        server["user"] = user
        server["recipients"] = list(set(server.get("recipients", []) + [user]))

        end_timestamp = server["start"] + time
        end_time = datetime.fromtimestamp(end_timestamp).strftime("%Y-%m-%d %H:%M:%S")

        await task_scheduler.occupy_warning(ip, ssh_user, ssh_pass, user, end_time)

        warn_delay = max(time - 300, 0)
        if warn_delay > 0:
            warn_task_id = f"device_warn_{ip.replace('.', '_')}"
            warn_success = await scheduler.schedule_task(
                task_id=warn_task_id,
                delay_seconds=warn_delay,
                task_func=task_scheduler.init_server_warning,
                device_id=server_id,
            )
            if warn_success:
                LOG.info(f"Scheduled warning task {warn_task_id} (delay={warn_delay}s)")
            else:
                LOG.error(f"Failed to schedule warning task {warn_task_id}")

        task_id = f"device_cleanup_{ip.replace('.', '_')}"
        success = await scheduler.schedule_task(
            task_id=task_id,
            delay_seconds=time,
            task_func=task_scheduler.init_server_warning,
            device_id=server_id,
            now=True
        )
        if success:
            LOG.info(f"Scheduled cleanup task {task_id} (delay={time}s)")
        else:
            LOG.error(f"Failed to schedule auto cleanup task {task_id}")

    else:
        await task_scheduler.init_warning(ip, ssh_user, ssh_pass)

        warn_task_id = f"device_warn_{ip.replace('.', '_')}"
        warn_success = await scheduler.cancel_task(warn_task_id)
        if warn_success:
            LOG.info(f"Cancelled warning task {warn_task_id}")
        else:
            LOG.info(f"Failed to cancel warning task {warn_task_id}")

        task_id = f"device_cleanup_{ip.replace('.', '_')}"
        success = await scheduler.cancel_task(task_id)
        if success:
            LOG.info(f"Cancelled cleanup task {task_id}")
        else:
            LOG.info(f"Failed to cancel cleanup task {task_id}")

        await task_scheduler.send_server_reminder(server, True)
        await task_scheduler.send_feishu_group_message(server, True)
        server["user"] = ""

    db.update(SERVER_COLLECTION, {"id": server_id}, server)

    LOG.info("occupy_server finished.")
    return server


@router.patch("/servers/{server_id}/focus")
async def focus_server(server_id: str, data: server_schemas.FocusRequest,
                       user=Depends(authenticate_user)):
    """following/unfollowing server"""

    try:
        server = db.find_one(SERVER_COLLECTION, {"id": server_id})
    except Exception as e:
        LOG.warning(f"Server {server_id} not found.")
        raise HTTPException(status_code=404, detail=f"{e}")

    recipients = server.get("recipients", [])
    if data.focus:
        server["recipients"] = list(set(recipients + [user]))
        LOG.info(f"User {user} followed server {server['device']['ip']}.")
    else:
        server["recipients"] = [r for r in recipients if r != user]
        LOG.info(f"User {user} unfollowed server {server['device']['ip']}.")

    db.update(SERVER_COLLECTION, {"id": server_id}, server)


@router.get("/servers/{server_id}/boot-entries",
            response_model=server_schemas.BootEntriesResponse)
async def get_boot_entries(server_id: str):
    """
    Get all boot entries (name + parent disk), current boot, next boot, and default boot
    """
    LOG.info(f"Received request to get boot entries for server {server_id}")
    try:
        server = db.find_one(SERVER_COLLECTION, {"id": server_id})
    except Exception as e:
        LOG.warning(f"Server {server_id} not found for boot entries query")
        raise HTTPException(status_code=404, detail=f"{e}")

    credentials_user = server["device"].get("username")
    credentials_pwd = server["device"].get("password")
    if not credentials_user or not credentials_pwd:
        raise HTTPException(
            status_code=400, detail="No saved OS credentials found for this server")

    LOG.info(f"Retrieving boot entries from server {server_id} ({server['device']['ip']})")
    entries, current_boot, next_boot, default_boot = await common_utils.get_boot_entries(
        server["device"]["ip"], credentials_user, credentials_pwd)

    LOG.info(f"Found {len(entries)} boot entries for server {server_id}")
    return {
        "entries": entries,
        "current": current_boot,
        "next": next_boot,
        "default": default_boot
    }


@router.post("/servers/{server_id}/set-boot")
async def set_boot_entry(
    server_id: str, 
    boot_id: str = Query(...),
    set_default: bool = Query(False),
):
    """
    Set boot entry for bare metal server
    """
    LOG.info(
        f"Received request to set boot entry {boot_id} for server {server_id}, "
        f"set_default: {set_default}"
    )

    try:
        server = db.find_one(SERVER_COLLECTION, {"id": server_id})
    except Exception:
        LOG.warning(f"Server {server_id} not found for set boot operation")
        raise HTTPException(status_code=404, detail="bare metal not found")

    credentials_user = server["device"].get("username")
    credentials_pwd = server["device"].get("password")
    if not credentials_user or not credentials_pwd:
        raise HTTPException(
            status_code=400, detail="No saved OS credentials found for this server")

    LOG.info(f"Setting next boot entry {boot_id} on server {server_id} ({server['device']['ip']})")
    await ssh_execute_async(server['device']['ip'],
                            f"efibootmgr -n {boot_id}", credentials_user, credentials_pwd)

    if set_default:
        LOG.info(f"Setting default boot entry {boot_id} on server"
                 f" {server_id} ({server['device']['ip']})")
        out = await ssh_execute_async(server['device']['ip'], "efibootmgr | grep BootOrder",
                                      credentials_user, credentials_pwd)
        boot_order_line = out.strip().split(":")[-1].strip()
        boot_list = boot_order_line.split(",")
        if boot_id in boot_list:
            boot_list.remove(boot_id)
        new_order = ",".join([boot_id] + boot_list)
        await ssh_execute_async(server['device']['ip'], f"efibootmgr -o {new_order}",
                                credentials_user, credentials_pwd)
        LOG.info(f"Default boot entry set to {boot_id} with order {new_order}")

    return {"message": (f"BootNext set to {boot_id} on {server['device']['ip']}"
                        f"{' (default updated)' if set_default else ''}")}


@router.get("/servers/{server_id}/nics", response_model=List[Union[server_schemas.NicBase,
                                                                   server_schemas.AIDPU_Nic]])
async def get_nic_information(server_id: str):
    LOG.info(f"Requesting NIC information for server_id: {server_id}")

    try:
        server = db.find_one(SERVER_COLLECTION, {"id": server_id})
    except Exception as e:
        LOG.warning(f"Server {server_id} not found.")
        raise HTTPException(status_code=404, detail=f"{e}")

    nics = await common_utils.collect_nic_info(
        server["device"]["ip"],
        server["device"].get("username", ""),
        server["device"].get("password", "")
    )

    LOG.info(f"Collected {len(nics)} NIC entries for server {server_id}")

    server["nics"] = nics

    db.update(SERVER_COLLECTION, {"id": server_id}, server)

    LOG.info(f'Returning NIC info for server {server["device"]["ip"]}')
    return nics


@router.get("/servers/{server_id}/hw", response_model=server_schemas.DeviceResponse)
async def get_hw_information(server_id: str):
    LOG.info(f"Requesting hardware information for server_id: {server_id}")

    try:
        server = db.find_one(SERVER_COLLECTION, {"id": server_id})
    except Exception as e:
        LOG.warning(f"Server {server_id} not found.")
        raise HTTPException(status_code=404, detail=f"{e}")

    device = await common_utils.collect_device_info(
        server["device"]["ip"],
        server["device"].get("username", ""),
        server["device"].get("password", "")
    )
    server["device"].update(device)

    db.update(SERVER_COLLECTION, {"id": server_id}, server)

    LOG.info(f'Returning hardware info for server {server["device"]["ip"]}')
    device["ip"] = server["device"]["ip"]
    device["username"] = server["device"].get("username", "")
    return device


@router.post("/servers/{server_id}/power-cycle")
async def power_cycle_server(server_id: str):
    """
    Power cycle bare metal server via BMC
    """
    LOG.info(f"Received request to power cycle server {server_id}")
    try:
        server = db.find_one(SERVER_COLLECTION, {"id": server_id})
    except Exception:
        LOG.warning(f"Server {server_id} not found for power cycle")
        raise HTTPException(status_code=404, detail="bare metal not found")

    bmcip = server["bmc"]["ip"]
    LOG.info(f"Power cycling server {server_id} via BMC {bmcip}")
    common_utils.ipmi_power_action(bmcip, "cycle")

    LOG.info(f"Successfully completed power cycle for server {server_id}")
    return {"message": f"Server {server_id} power cycled via BMC {bmcip}"}


@router.post("/servers/{server_id}/power-reset")
async def power_reset_server(server_id: str):
    """
    Warm reset bare metal server via BMC
    """
    LOG.info(f"Received request to power reset server {server_id}")
    try:
        server = db.find_one(SERVER_COLLECTION, {"id": server_id})
    except Exception:
        LOG.warning(f"Server {server_id} not found for power reset")
        raise HTTPException(status_code=404, detail="bare metal not found")

    bmcip = server["bmc"]["ip"]
    LOG.info(f"Power resetting server {server_id} via BMC {bmcip}")
    common_utils.ipmi_power_action(bmcip, "reset")

    LOG.info(f"Successfully completed power reset for server {server_id}")
    return {"message": f"Server {server_id} warm rebooted via BMC {bmcip}"}


@router.post("/servers/{server_id}/update_mcr", status_code=202)
async def update_mcr(server_id: str, data: common_schemas.MCRRequest):
    LOG.info("Received MCR update request for server_id="
             f"{server_id} with options={data.update_options}")

    # Fetch server information
    try:
        server = db.find_one(SERVER_COLLECTION, {"id": server_id})
        if not server:
            LOG.warning(f"Server {server_id} not found in database")
            raise HTTPException(status_code=404, detail="bare metal not found")
        LOG.debug(f"Fetched server info: {server}")
    except Exception as e:
        LOG.error(f"Failed to fetch server {server_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch server info")

    # Create a task entry
    task_id = common_utils.create_mcr_task(server_id, data.update_options)
    LOG.info(f"Created MCR update task {task_id} for server {server_id}")

    server["task_id"] = task_id
    db.update(SERVER_COLLECTION, {"id": server_id}, server)

    asyncio.create_task(
        common_utils.run_mcr_update_task(
            task_id,
            server["device"]["ip"],
            server["device"]["username"],
            server["device"]["password"],
            server["bmc"]["ip"],
            data
        )
    )

    LOG.info(f"Async MCR update task {task_id} started for server {server_id}")

    return {"message": "MCR update task accepted", "task_id": task_id}
