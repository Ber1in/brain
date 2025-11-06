# Copyright (C) 2021 - 2025, Shanghai Yunsilicon Technology Co., Ltd.
# All rights reserved.

from datetime import datetime
from uuid import uuid4
from fastapi import APIRouter, Depends, status, HTTPException
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

    vpd_res = ssh_execute(ip, "yuncli vpd -r", user, password)
    nics = tools.parse_yuncli_vpd(vpd_res)
    mac_res = ssh_execute(ip, "yuncli mac -r", user, password)
    macs = tools.parse_bdf_mac(mac_res)
    for nic in nics:
        nic["mac"] = macs[nic["bdf"]]

    entries, _, _, _ = tools.get_boot_entries(
        ip, user, password)
    return device_sn, nics, entries


@router.post("/devices", response_model=device_schemas.ServerDetailResponse)
async def create_device(data: device_schemas.ServerRequest):
    LOG.info(f"Creating device, IP: {data.device.ip}, BMC hostname: {data.bmc.hostname}")

    # exist = db.find(SERVER_COLLECTION, {"device.ip": str(data.device.ip)})
    # if exist:
    #     LOG.warning(f"Device already exists, IP: {data.device.ip}")
    #     raise HTTPException(
    #         status_code=400,
    #         detail=f"Device with IP {data.device.ip} already exists"
    #     )

    device_sn, nics, entries = _update_automatic(
        str(data.device.ip), data.device.username, data.device.password
    )
    LOG.info(f"Auto discovery completed, SN: {device_sn}, NICs: {len(nics)}")

    bmc_ip = '.'.join((lambda p: p[:-2] + ['2'] + p[-1:])(str(data.device.ip).split('.')))

    result = {
        "bmc": {
            "ip": bmc_ip,
            "hostname": data.bmc.hostname},
        "device": {
            "sn": device_sn,
            "ip": str(data.device.ip),
            "username": data.device.username,
            "password": data.device.password
        },
        "nics": nics,
        "os_types": list(entries.values()),
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
# 先删除已有的警告块
sed -i '/# WARNING_MESSAGE_START/,/# WARNING_MESSAGE_END/d' /etc/profile

# 添加新的警告块
cat >> /etc/profile << 'EOF'
# WARNING_MESSAGE_START
echo "-----------------------------------------------------------------------------"
echo "提示：当前服务器无人使用！"
echo "请先登录: http://10.0.3.206:8089/devices 在[服务器管理]完成'占用服务器'后继续使用"
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
        ssh_execute(server["device"]["ip"], clean_command, server["device"]["username"], server["device"]["password"])
    except Exception:
        LOG.warning("Failed to initialize the server usage warning message.")


@router.get("/devices", response_model=list[device_schemas.ServerDetailResponse])
async def get_all_devices():
    LOG.info("Fetching all devices")
    devices = db.find(SERVER_COLLECTION, {})
    for i in devices:
        if i["time"]:
            now = datetime.now().timestamp()
            start = i.get("start")  # start 是任务开始的时间戳
            passed = int(now - start)  # 已经过了多少秒
            remaining = i["time"] - passed  # 剩余时间 = 原定总秒数 - 已经过秒数
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

    device = db.find_one(SERVER_COLLECTION, {"id": device_id})
    if not device:
        LOG.warning(f"Device not found, ID: {device_id}")
        raise HTTPException(status_code=404, detail="Device not found")

    if data.auto:
        LOG.info(f"Automatic updating device: {device_id}")

        device_sn, nics, entries = _update_automatic(
            device["device"]["ip"],
            device["device"].get("username", ""),
            device["device"].get("password", "")
        )
        device["device"]["sn"] = device_sn
        device["nics"] = nics
        device["os_types"] = list(entries.values())

    else:
        LOG.info(f"Manual updating device: {device_id}")

        if data.device and data.device.password:
            device["device"]["password"] = data.device.password

        if data.bmc and data.bmc.hostname:
            device["bmc"]["hostname"] = data.bmc.hostname

        if data.tags is not None:
            device["tags"] = data.tags

        if data.notes is not None:
            device["notes"] = data.notes

        if data.time is not None:
            device["time"] = data.time
            device["start"] = datetime.now().timestamp()
            ip = device["device"]["ip"]
            ssh_user = device["device"].get("username", "")
            ssh_pass = device["device"].get("password", "")
            time = int(data.time)
            if time:
                device["user"] = user

                # 计算结束时间戳并转换为指定格式
                end_timestamp = device["start"] + time
                end_time = datetime.fromtimestamp(end_timestamp).strftime("%Y-%m-%d %H:%M:%S")

                # 使用更可靠的方法：先删除再添加
                command = f'''
# 先删除已有的警告块
sed -i '/# WARNING_MESSAGE_START/,/# WARNING_MESSAGE_END/d' /etc/profile

# 添加新的警告块
cat >> /etc/profile << 'EOF'
# WARNING_MESSAGE_START
echo "--------------------------------------------------------------------"
echo "警告：当前服务器有人正在使用！请勿执行破坏性操作！"
echo "使用人: {user}"
echo "占用截止时间: {end_time}"
echo "请登录: http://10.0.3.206:8089/devices 在[服务器管理]页面查看其余可用服务器"
echo "--------------------------------------------------------------------"
# WARNING_MESSAGE_END
EOF
'''

                ssh_execute(ip, command, ssh_user, ssh_pass)

            else:
                device["user"] = ""
                # 删除警告
                clean_command = '''
# 先删除已有的警告块
sed -i '/# WARNING_MESSAGE_START/,/# WARNING_MESSAGE_END/d' /etc/profile

# 添加新的警告块
cat >> /etc/profile << 'EOF'
# WARNING_MESSAGE_START
echo "-----------------------------------------------------------------------------"
echo "提示：当前服务器无人使用！"
echo "请先登录: http://10.0.3.206:8089/devices 在[服务器管理]完成'占用服务器'后继续使用"
echo "-----------------------------------------------------------------------------"
# WARNING_MESSAGE_END
EOF
'''
                ssh_execute(ip, clean_command, ssh_user, ssh_pass)

    device["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    db.update(SERVER_COLLECTION, {"id": device_id}, device)

    LOG.info(f"Device updated, ID: {device_id}, user: {user}, time: {device.get('time', 0)}")
    return device
