# Copyright (C) 2021 - 2025, Shanghai Yunsilicon Technology Co., Ltd.
# All rights reserved.


from collections import defaultdict
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
    Parse yuncli lspci output and return a list of devices.
    If multiple devices have the same Product Name + Part number + Serial number,
    only return sn and type; otherwise, include bdf as well.
    Skip entries that do not have all three: Product Name, Part number, Serial number.
    """
    devices = []
    current = {}

    # Parse the raw output
    for line in output.splitlines():
        line = line.strip()

        # Match BDF
        m = re.match(r"^([0-9a-fA-F]{2}:[0-9a-fA-F]{2}\.\d)\s+Ethernet controller", line)
        if m:
            # Only append if current has all required fields
            if current and all(k in current for k in (
                    "Product Name", "Part number", "Serial number")):
                devices.append(current)
            current = {"bdf": m.group(1)}
            continue

        # Match Product Name
        m = re.match(r"Product Name:\s*(.+)", line)
        if m:
            current["Product Name"] = m.group(1)
            continue

        # Match Part number
        m = re.match(r"\[PN\]\s*Part number:\s*(.+)", line)
        if m:
            current["Part number"] = m.group(1)
            continue

        # Match Serial number
        m = re.match(r"\[SN\]\s*Serial number:\s*(.+)", line)
        if m:
            current["Serial number"] = m.group(1)
            continue

    # Append the last device if it has all required fields
    if current and all(k in current for k in ("Product Name", "Part number", "Serial number")):
        devices.append(current)

    # Count occurrences of each unique Product+Part+SN combination
    counter = defaultdict(list)
    for d in devices:
        key = (d.get("Product Name"), d.get("Part number"), d.get("Serial number"))
        counter[key].append(d)

    # Build final output
    result = []
    for key, dev_list in counter.items():
        prod_name, part_num, sn = key
        if len(dev_list) > 1:
            # Duplicate, return only sn and type
            result.append({"sn": sn, "type": prod_name})
        else:
            # Unique, return sn, type, bdf
            result.append({
                "sn": sn,
                "type": prod_name,
                "bdf": dev_list[0].get("bdf")
            })

    return result


# def parse_yuncli_vpd(output: str) -> List[Dict[str, str]]:
#     """
#     Parse 'yuncli vpd -r' output and extract BDF, Product Name, and SN.
#     """
#     devices = []
#     current_device = {}

#     for line in output.splitlines():
#         line = line.strip()
#         if not line:
#             continue

#         # BDF line
#         bdf_match = re.match(r"BDF:(\S+):", line)
#         if bdf_match:
#             if current_device:
#                 devices.append(current_device)
#                 current_device = {}
#             current_device["bdf"] = bdf_match.group(1)
#             continue

#         # Product Name
#         prod_match = re.match(r"Product Name:\s+(.*)", line)
#         if prod_match:
#             current_device["type"] = prod_match.group(1).strip()
#             continue

#         # Serial Number
#         sn_match = re.match(r"Serial Number\[SN\]:\s+(.*)", line)
#         if sn_match:
#             current_device["sn"] = sn_match.group(1).strip()
#             continue

#     # append the last device
#     if current_device:
#         devices.append(current_device)

#     return devices


def parse_bdf_mac(output: str) -> Dict[str, List[str]]:
    """
    Parse output of `yuncli mac -r` into a dict {bdf: [mac1, mac2, ...]}
    Remove leading '0000:' from BDF.
    """
    result = {}
    current_bdf = None
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        bdf_match = re.match(r'BDF:([0-9a-fA-F:.]+):', line)
        if bdf_match:
            raw_bdf = bdf_match.group(1)
            # Remove leading '0000:' if present
            if raw_bdf.startswith('0000:'):
                raw_bdf = raw_bdf[5:]
            current_bdf = raw_bdf
            result[current_bdf] = []
        else:
            if current_bdf:
                parts = line.split()
                if len(parts) == 2:
                    mac = parts[1]
                    result[current_bdf].append(mac)
    return result


def get_boot_entries(host_ip, user, pwd):
    efiboot_output = ssh_execute(host_ip, "efibootmgr -v", user, pwd).splitlines()
    lsblk_output = ssh_execute(
        host_ip, "lsblk -rno NAME,PKNAME,PTTYPE,PARTUUID", user, pwd).splitlines()

    uuid_to_disk = {}
    for line in lsblk_output:
        parts = line.strip().split()
        if len(parts) == 4:
            name, parent, pttype, partuuid = parts
            partuuid = partuuid.lower() if partuuid != "-" else ""
            if pttype == "gpt" and partuuid:
                uuid_to_disk[partuuid] = parent or name
            elif pttype in ("dos", "mbr") and partuuid:
                disk_sig = partuuid.split("-")[0]
                uuid_to_disk[partuuid] = parent or name
                uuid_to_disk[disk_sig] = parent or name

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

            skip_keywords = ["UEFI: PXE", "EFI Shell",
                             "EFI DVD/CDROM", "EFI Network", "CD-ROM", "DVD", "PXE"]
            if any(keyword in line for keyword in skip_keywords):
                continue
            if "HD(" not in line and "File(\\EFI" not in line:
                continue

            partuuid = ""
            gpt_match = re.search(r"GPT,([0-9a-fA-F-]+)", line)
            mbr_match = re.search(r"MBR,(0x[0-9a-fA-F]+)", line)

            if gpt_match:
                partuuid = gpt_match.group(1).lower()
            elif mbr_match:
                mbr_sig = mbr_match.group(1).lower().replace("0x", "")
                for key in uuid_to_disk.keys():
                    if key.startswith(mbr_sig):
                        partuuid = key
                        break

            disk = uuid_to_disk.get(partuuid, "")

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