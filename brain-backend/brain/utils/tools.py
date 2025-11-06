# Copyright (C) 2021 - 2025, Shanghai Yunsilicon Technology Co., Ltd.
# All rights reserved.


import logging
import re
import subprocess
from typing import Dict, List
from fastapi import HTTPException

from brain.utils.ssh_client import ssh_execute

LOG = logging.getLogger(__name__)
BMC_USER = "ipmiadmin"
BMC_PASS = "ymxl@2022"


def parse_yuncli_vpd(output: str) -> List[Dict[str, str]]:
    """
    Parse 'yuncli vpd -r' output and extract BDF, Product Name, and SN.
    """
    devices = []
    current_device = {}

    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue

        # BDF line
        bdf_match = re.match(r"BDF:(\S+):", line)
        if bdf_match:
            if current_device:
                devices.append(current_device)
                current_device = {}
            current_device["bdf"] = bdf_match.group(1)
            continue

        # Product Name
        prod_match = re.match(r"Product Name:\s+(.*)", line)
        if prod_match:
            current_device["type"] = prod_match.group(1).strip()
            continue

        # Serial Number
        sn_match = re.match(r"Serial Number\[SN\]:\s+(.*)", line)
        if sn_match:
            current_device["sn"] = sn_match.group(1).strip()
            continue

    # append the last device
    if current_device:
        devices.append(current_device)

    return devices


def parse_bdf_mac(output: str):
    """
    Parse output of `yuncli mac -r` into a dict {bdf: [mac1, mac2, ...]}
    """
    result = {}
    current_bdf = None
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        # 匹配 BDF 行
        bdf_match = re.match(r'BDF:([0-9a-fA-F:.]+):', line)
        if bdf_match:
            current_bdf = bdf_match.group(1)
            result[current_bdf] = []
        else:
            # 匹配 mac 行
            if current_bdf:
                parts = line.split()
                if len(parts) == 2:
                    mac = parts[1]
                    result[current_bdf].append(mac)
    return result


def get_boot_entries(host_ip, user, pwd):
    # 获取 efibootmgr 输出
    efiboot_output = ssh_execute(host_ip, "efibootmgr -v", user, pwd).splitlines()
    # 获取 lsblk 输出，包括 PARTUUID、父磁盘名和分区表类型
    lsblk_output = ssh_execute(
        host_ip, "lsblk -rno NAME,PKNAME,PTTYPE,PARTUUID", user, pwd).splitlines()

    # 构建映射：PARTUUID/MbrSignature -> disk
    uuid_to_disk = {}
    for line in lsblk_output:
        parts = line.strip().split()
        if len(parts) == 4:
            name, parent, pttype, partuuid = parts
            partuuid = partuuid.lower() if partuuid != "-" else ""
            # 处理 GPT 分区
            if pttype == "gpt" and partuuid:
                uuid_to_disk[partuuid] = parent or name
            # 处理 MBR 分区（内核伪造的 ID，如 a38f2887-01）
            elif pttype in ("dos", "mbr") and partuuid:
                # 去掉 -01 等后缀，保存成磁盘签名形式 a38f2887
                disk_sig = partuuid.split("-")[0]
                uuid_to_disk[partuuid] = parent or name
                uuid_to_disk[disk_sig] = parent or name  # 支持按磁盘签名匹配

    entries = {}
    current_boot = None
    next_boot = None
    default_boot = None

    for line in efiboot_output:
        line = line.strip()
        if line.startswith("BootCurrent"):
            current_boot = line.split(":")[1].strip()
        elif line.startswith("BootNext"):
            next_boot = line.split(":")[1].strip()
        elif line.startswith("BootOrder"):
            parts = line.split(":")[1].strip().split(",")
            default_boot = parts[0] if parts else None
        elif line.startswith("Boot") and "*" in line:
            boot_num, rest = line.split("*", 1)
            boot_num = boot_num.strip().replace("Boot", "")
            name = rest.strip().split("\t")[0]

            # 跳过非硬盘启动项
            skip_keywords = ["UEFI: PXE", "EFI Shell",
                             "EFI DVD/CDROM", "EFI Network", "CD-ROM", "DVD", "PXE"]
            if any(keyword in line for keyword in skip_keywords):
                continue
            if "HD(" not in line and "File(\\EFI" not in line:
                continue

            # 提取 GPT 或 MBR 标识
            partuuid = ""
            gpt_match = re.search(r"GPT,([0-9a-fA-F-]+)", line)
            mbr_match = re.search(r"MBR,(0x[0-9a-fA-F]+)", line)

            if gpt_match:
                partuuid = gpt_match.group(1).lower()
            elif mbr_match:
                # MBR 磁盘签名（例如 0xa38f2887）
                mbr_sig = mbr_match.group(1).lower().replace("0x", "")
                # 在映射中查找匹配项
                for key in uuid_to_disk.keys():
                    if key.startswith(mbr_sig):
                        partuuid = key
                        break

            # 查找对应磁盘名
            disk = uuid_to_disk.get(partuuid, "")

            # 构造显示文本
            entry_text = name
            if disk:
                entry_text = f"{entry_text} ({disk})"
            if partuuid:
                entry_text = f"{entry_text} [{partuuid}]"

            entries[boot_num] = entry_text

    return entries, current_boot, next_boot, default_boot


def ipmi_power_action(bmcip: str, action: str):
    """Execute IPMI power action via ipmitool command"""
    LOG.info(f"Executing IPMI {action} on BMC {bmcip}")

    if action not in ("cycle", "reset"):
        raise HTTPException(status_code=400, detail=f"Unsupported IPMI action: {action}")

    cmd = ["ipmitool", "-I", "lanplus", "-H", bmcip, "-U", BMC_USER, "-P", BMC_PASS,
           "chassis", "power", action]

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