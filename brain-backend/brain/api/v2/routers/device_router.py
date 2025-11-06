# Copyright (C) 2021 - 2025, Shanghai Yunsilicon Technology Co., Ltd.
# All rights reserved.

from datetime import datetime
from uuid import uuid4
from fastapi import APIRouter, Depends, status, HTTPException, Query
import logging

from brain.auth import authenticate_user
from brain.api.v2.schemas import device_schemas
from brain.json_db import SQLiteDocumentDB
from brain.utils.ssh_client import ssh_execute
from brain.utils import tools


LOG = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(authenticate_user)])
BMC_USER = "ipmiadmin"
BMC_PASS = "ymxl@2022"
db = SQLiteDocumentDB()
SERVER_COLLECTION = "servers"


def _update_automatic(ip, user, password):
    device_sn = ssh_execute(ip, "dmidecode -s system-serial-number", user, password)

    # vpd_res = ssh_execute(ip, "yuncli vpd -r", user, password)
    cmd = ("lspci -d 1f67: -vvv | awk '/Ethernet controller/ {print} /Vital Product Data/ "
           "{print; for(i=0;i<5;i++){getline; print}}'")
    vpd_res = ssh_execute(ip, cmd, user, password)
    nics = tools.parse_yuncli_vpd(vpd_res)
    mac_res = ssh_execute(ip, "yuncli mac -r", user, password)
    macs = tools.parse_bdf_mac(mac_res)
    for nic in nics:
        bdf = nic.get('bdf')
        if bdf and bdf in macs:
            nic['mac'] = macs[bdf]

    iface_name = ssh_execute(
        ip,
        ("ip route get 10.0.3.248 | head -1 | awk '{for(i=1;i<=NF;i++)"
         " if($i==\"dev\") print $(i+1)}'"), 
        user, password)

    iface_mac = ssh_execute(ip, f"cat /sys/class/net/{iface_name}/address", user, password).strip()
    gateway = ssh_execute(ip, "ip route | awk '/default/ {print $3}'", user, password).strip()

    device_info = {
        "sn": device_sn,
        "mac": iface_mac,
        "gateway": gateway
    }
    return device_info, nics


@router.post("/devices", response_model=device_schemas.ServerDetailResponse)
async def create_device(data: device_schemas.ServerRequest):
    LOG.info(f"Creating device, IP: {data.device.ip}, BMC hostname: {data.bmc.hostname}")

    exist = db.find(SERVER_COLLECTION,
                    {"json_extract(device, '$.ip')": str(data.device.ip)})
    if exist:
        LOG.warning(f"Device already exists, IP: {data.device.ip}")
        raise HTTPException(
            status_code=400,
            detail=f"Device with IP {data.device.ip} already exists"
        )

    device, nics = _update_automatic(
        str(data.device.ip), data.device.username, data.device.password
    )
    LOG.info(f"Auto discovery completed, SN: {device['sn']}, NICs: {len(nics)}")

    bmc_ip = '.'.join((lambda p: p[:-2] + ['2'] + p[-1:])(str(data.device.ip).split('.')))

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
    }

    db.insert(SERVER_COLLECTION, result)
    LOG.info(f"Device created, ID: {result['id']}")

    try:
        init_command = '''
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
        ssh_execute(str(data.device.ip), init_command, data.device.username, data.device.password)
    except Exception:
        LOG.warning("Failed to initialize the server usage warning message.")

    return result


@router.delete("/devices/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_device(device_id: str):
    LOG.info(f"Deleting device, ID: {device_id}")
    try:
        server = db.find_one(SERVER_COLLECTION, {"id": device_id})
    except Exception as e:
        LOG.warning(f"Device not found, {e}")
        raise HTTPException(status_code=404, detail=f"Device not found, {e}")

    deleted = db.delete(SERVER_COLLECTION, {"id": device_id})
    if not deleted:
        LOG.warning(f"Device not found, ID: {device_id}")
    else:
        LOG.info(f"Device deleted, ID: {device_id}")

    try:
        clean_command = "sed -i '/# WARNING_MESSAGE_START/,/# WARNING_MESSAGE_END/d' /etc/profile"
        ssh_execute(server["device"]["ip"], clean_command, server["device"]
                    ["username"], server["device"]["password"])
    except Exception:
        LOG.warning("Failed to initialize the server usage warning message.")


@router.get("/devices", response_model=list[device_schemas.ServerDetailResponse])
async def get_all_devices():
    LOG.info("Fetching all devices")
    devices = db.find(SERVER_COLLECTION, {})
    for i in devices:
        if i["time"]:
            now = datetime.now().timestamp()
            start = i.get("start")
            passed = int(now - start)
            remaining = i["time"] - passed
            i["time"] = max(remaining, 0)
    LOG.info(f"Total devices fetched: {len(devices)}")
    return devices


@router.get("/devices/{device_id}", response_model=device_schemas.ServerDetailResponse)
async def get_device(device_id: str):
    LOG.info(f"Fetching device, ID: {device_id}")
    try:
        device = db.find_one(SERVER_COLLECTION, {"id": device_id})
        if device["time"]:
            now = datetime.now().timestamp()
            start = device.get("start")
            passed = int(now - start)
            remaining = device["time"] - passed
            device["time"] = max(remaining, 0)
    except Exception as e:
        LOG.warning(f"Device not found, {e}")
        raise HTTPException(status_code=404, detail=f"Device not found, {e}")

    LOG.info(f"Device fetched: ID={device_id}")
    return device


@router.put("/devices/{device_id}", response_model=device_schemas.ServerDetailResponse)
async def update_device(
    device_id: str,
    data: device_schemas.ServerUpdateRequest,
    user=Depends(authenticate_user)
):
    LOG.info(f"Updating device, ID: {device_id}, auto: {data.auto}, user: {user}")

    server = db.find_one(SERVER_COLLECTION, {"id": device_id})
    if not server:
        LOG.warning(f"Device not found, ID: {device_id}")
        raise HTTPException(status_code=404, detail="Device not found")

    if data.auto:
        LOG.info(f"Automatic updating device: {device_id}")

        device, nics = _update_automatic(
            server["device"]["ip"],
            server["device"].get("username", ""),
            server["device"].get("password", "")
        )
        server["device"].update(device)
        server["nics"] = nics

    else:
        LOG.info(f"Manual updating device: {device_id}")

        if data.device and data.device.password:
            server["device"]["password"] = data.device.password

        if data.bmc and data.bmc.hostname:
            server["bmc"]["hostname"] = data.bmc.hostname

        if data.tags is not None:
            server["tags"] = data.tags

        if data.notes is not None:
            server["notes"] = data.notes

        if data.time is not None:
            server["time"] = data.time
            server["start"] = datetime.now().timestamp()
            ip = server["device"]["ip"]
            ssh_user = server["device"].get("username", "")
            ssh_pass = server["device"].get("password", "")
            time = int(data.time)
            if time:
                server["user"] = user

                end_timestamp = server["start"] + time
                end_time = datetime.fromtimestamp(end_timestamp).strftime("%Y-%m-%d %H:%M:%S")

                command = f'''
sed -i '/# WARNING_MESSAGE_START/,/# WARNING_MESSAGE_END/d' /etc/profile

cat >> /etc/profile << 'EOF'
# WARNING_MESSAGE_START
echo "--------------------------------------------------------------------"
echo "警告：当前服务器有人正在使用！请勿执行破坏性操作！"
echo "使用人: {user}"
echo "占用截止时间: {end_time}"
echo "请登录: http://10.0.3.248:8089/devices 在[服务器管理]页面查看其余可用服务器"
echo "--------------------------------------------------------------------"
# WARNING_MESSAGE_END
EOF
'''

                ssh_execute(ip, command, ssh_user, ssh_pass)

            else:
                server["user"] = ""
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
                ssh_execute(ip, clean_command, ssh_user, ssh_pass)

    server["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    db.update(SERVER_COLLECTION, {"id": device_id}, server)

    LOG.info(f"Device updated, ID: {device_id}, user: {user}, time: {server.get('time', 0)}")
    return server


@router.get("/devices/{server_id}/boot-entries",
            response_model=device_schemas.BootEntriesResponse)
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
    entries, current_boot, next_boot, default_boot = tools.get_boot_entries(
        server["device"]["ip"], credentials_user, credentials_pwd)

    LOG.info(f"Found {len(entries)} boot entries for server {server_id}")
    return {
        "entries": entries,
        "current": current_boot,
        "next": next_boot,
        "default": default_boot
    }


@router.post("/devices/{server_id}/set-boot")
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
    ssh_execute(server['device']['ip'],
                f"efibootmgr -n {boot_id}", credentials_user, credentials_pwd)

    if set_default:
        LOG.info(f"Setting default boot entry {boot_id} on server"
                 f" {server_id} ({server['device']['ip']})")
        out = ssh_execute(server['device']['ip'], "efibootmgr | grep BootOrder",
                          credentials_user, credentials_pwd)
        boot_order_line = out.strip().split(":")[-1].strip()
        boot_list = boot_order_line.split(",")
        if boot_id in boot_list:
            boot_list.remove(boot_id)
        new_order = ",".join([boot_id] + boot_list)
        ssh_execute(server['device']['ip'], f"efibootmgr -o {new_order}",
                    credentials_user, credentials_pwd)
        LOG.info(f"Default boot entry set to {boot_id} with order {new_order}")

    return {"message": (f"BootNext set to {boot_id} on {server['device']['ip']}"
                        f"{' (default updated)' if set_default else ''}")}


@router.post("/devices/{server_id}/power-cycle")
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
    tools.ipmi_power_action(bmcip, "cycle")

    LOG.info(f"Successfully completed power cycle for server {server_id}")
    return {"message": f"Server {server_id} power cycled via BMC {bmcip}"}


@router.post("/devices/{server_id}/power-reset")
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
    tools.ipmi_power_action(bmcip, "reset")

    LOG.info(f"Successfully completed power reset for server {server_id}")
    return {"message": f"Server {server_id} warm rebooted via BMC {bmcip}"}
