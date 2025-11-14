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


def parse_nics_info(output: str) -> List[Dict[str, str]]:
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
        result.append({
            "sn": sn,
            "type": prod_name,
            "nic_info": [{"bdf": d["bdf"]} for d in dev_list]
        })

    return result


def parse_bdf_mac(output: str) -> Dict[str, str]:
    """
    Parse `yuncli mac -r` output into {bdf_with_func: mac}
    e.g. {"b3:00.0": "xx:xx:xx:xx:xx:xx"}
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
            if raw_bdf.startswith('0000:'):
                raw_bdf = raw_bdf[5:]
            current_bdf = raw_bdf
            continue

        if current_bdf:
            parts = line.split()
            if len(parts) == 2:
                func, mac = parts
                try:
                    func = int(func)
                    full_bdf = f"{current_bdf[:-1]}{func}"
                    result[full_bdf] = mac
                except ValueError:
                    pass

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


def update_automatic(ip, user, password):
    server_sn = ssh_execute(ip, "cat /sys/class/dmi/id/product_serial", user, password)
    server_vendor = ssh_execute(ip, "cat /sys/class/dmi/id/sys_vendor", user, password)
    server_product = ssh_execute(ip, "cat /sys/class/dmi/id/product_name", user, password)

    cpu_cmd = (
        "lscpu | awk -F\":\" "
        "'/Architecture:|Vendor ID:|Model name:/ "
        "{gsub(/^[ \\t]+/, \"\", $2); print $2}'"
    )
    cpu_infos = ssh_execute(ip, cpu_cmd, user, password).strip().split("\n")

    # PCI VPD
    pci_cmd = ("lspci -d 1f67: -vvv | awk '/Ethernet controller/ {print} "
               "/Vital Product Data/ {print; for(i=0;i<5;i++){getline; print}}'")
    pci_res = ssh_execute(ip, pci_cmd, user, password)
    nics = parse_nics_info(pci_res)

    mac_res = ssh_execute(ip, "yuncli mac -r", user, password)
    macs = parse_bdf_mac(mac_res)

    # Remote iface map
    map_cmd = ("for i in /sys/class/net/*/address; do "
               "echo \"$(basename $(dirname $i)) $(cat $i)\"; "
               "done")
    out = ssh_execute(ip, map_cmd, user, password)

    remote_map = {}
    for raw in out.splitlines():
        line = raw.strip()

        if ((line.startswith('"') and line.endswith('"')) or
                (line.startswith("'") and line.endswith("'"))):
            line = line[1:-1].strip()

        if not line:
            continue

        parts = line.split()
        if len(parts) < 2:
            continue

        iface, mac = parts[0].strip(), parts[1].strip().lower()
        remote_map[mac] = iface

    for nic in nics:
        for info in nic["nic_info"]:
            mac = macs.get(info["bdf"])
            if not mac:
                continue

            info["mac"] = mac
            iface = remote_map.get(mac)
            if iface:
                info["iface"] = iface

    # Primary route interface
    route_cmd = ("ip route get 10.0.3.248 | head -1 | "
                 "awk '{for(i=1;i<=NF;i++) if($i==\"dev\") print $(i+1)}'")
    iface_name = ssh_execute(ip, route_cmd, user, password)

    iface_mac = ssh_execute(ip, f"cat /sys/class/net/{iface_name}/address", user, password).strip()
    gateway = ssh_execute(ip, "ip route | awk '/default/ {print $3}'", user, password).strip()

    device_info = {
        "sn": server_sn,
        "mac": iface_mac,
        "gateway": gateway,
        "vendor": server_vendor,
        "product": server_product,
        "arch": cpu_infos[0],
        "cpu_vendor": cpu_infos[1],
        "cpu_mode": cpu_infos[2]
    }
    return device_info, nics