# Copyright (C) 2021 - 2025, Shanghai Yunsilicon Technology Co., Ltd.
# All rights reserved.


import re
from typing import Dict, List

from brain.utils.ssh_client import ssh_execute


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
    efiboot_output = ssh_execute(host_ip, "efibootmgr -v", user, pwd).splitlines()
    lsblk_output = ssh_execute(host_ip, "lsblk -no PARTUUID,PKNAME", user, pwd).splitlines()

    uuid_to_disk = {}
    for line in lsblk_output:
        parts = line.strip().split()
        if len(parts) == 2:
            uuid, disk = parts
            uuid_to_disk[uuid.lower()] = disk

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
            boot_order_parts = line.split(":")[1].strip().split(",")
            default_boot = boot_order_parts[0] if boot_order_parts else None
        elif line.startswith("Boot") and "*" in line:
            boot_num, rest = line.split("*", 1)
            boot_num = boot_num.strip().replace("Boot", "")
            name = rest.strip().split("\t")[0]

            # 增强过滤条件 - 检查整个行内容
            skip_keywords = [
                "UEFI: PXE", 
                "EFI Shell", 
                "EFI DVD/CDROM",
                "EFI Network",
                "CD-ROM",
                "DVD",
                "PXE"
            ]

            # 如果包含任何要跳过的关键词，就跳过这个条目
            if any(keyword in line for keyword in skip_keywords):
                continue

            # 额外的硬盘设备检查 - 确保是硬盘启动项
            if "HD(" not in line and "File(\\EFI" not in line:
                continue

            # Extract PARTUUID from the boot entry
            partuuid = ""
            gpt_match = re.search(r"GPT,([0-9a-fA-F-]+)", line)
            mbr_match = re.search(r"MBR,(0x[0-9a-fA-F]+)", line)

            if gpt_match:
                partuuid = gpt_match.group(1).lower()
            elif mbr_match:
                partuuid = mbr_match.group(1).lower()

            # Get disk name from PARTUUID mapping
            disk = uuid_to_disk.get(partuuid, "")

            # Create entry with name, disk, and partuuid
            entry_text = name
            if disk:
                entry_text = f"{entry_text} ({disk})"
            if partuuid:
                entry_text = f"{entry_text} [{partuuid}]"

            entries[boot_num] = entry_text

    return entries, current_boot, next_boot, default_boot