# Copyright (C) 2021 - 2025, Shanghai Yunsilicon Technology Co., Ltd.
# All rights reserved.

import asyncio
from collections import defaultdict
from datetime import datetime
import logging
import os
import re
import subprocess
from typing import Dict, List
from uuid import uuid4
from fastapi import HTTPException

from brain.json_db import SQLiteDocumentDB
from brain.utils.ssh_client import ssh_execute_async
from brain.api.v2.schemas import common_schemas

LOG = logging.getLogger(__name__)
BMC_USER = "ipmiadmin"
BMC_PASS = "ymxl@2022"
COMMON_USER = "tester"
COMMON_USER_PASSWORD = "Test.999"
COMMON_SERVER = "10.0.3.248"
TASK_POOL_COLLECTION = "tasks"
db = SQLiteDocumentDB()
MELLANOX_ALIAS = {
    ""
}
PRODUCT_PART_NUMBER_DICT = {
    "90-0001-02": "MF200",
    "90-0002-02": "MC200",
    "90-0003-02": "MF50-019",
    "90-0004-02": "MC50-019",
    "90-0005-02": "MF50-023",
    "90-0006-02": "MC50-023",
    "90-0007-01": "Andes EVB",
    "90-0008-01": "MV200",
    "90-0009-01": "MS200-FHHL",
    "90-0010-01": "MC100",
    "90-0011-01": "MS200-HHHL",
    "90-0012-01": "MS50",
    "90-0013-01": "MS200s",
    "90-0014-01": "MS200 OCP3.0",
    "90-0015-01": "MS200_V2.0",
    "90-0016-01": "MS200s_V2.0",
    "90-0017-01": "PCIe Socket Direct card",
    "90-0018-01": "MS100s OCP3.0",
    "90-0019-01": "NCSI test card",
    "90-0020-01": "MC400s-浪潮版本",
    "90-0020-02": "MC400s-字节版本",
    "90-0021-01": "OCP3.0 test card",
    "90-0022-01": "MS200 OCP3.0_V2.0",
    "90-0023-01": "MS100s OCP3.0_V2.0",
    "90-0024-01": "MS200s-SL",
    "90-0025-01": "MC400s-SL",
    "90-0027-01": "MC400S-GA",
    "90-0026-01": "MF200-Multi-Host",
    "90-0028-01": "MS400",
    "90-0029-01": "MC400S-Verdi",
    "90-0030-01": "MC400-Verdi"
}


async def ensure_packages_installed(host: str, user: str, pwd: str, packages: list):
    """
    Ensure packages (interpreted as commands) exist on remote host.
    If not, install corresponding packages (assumed same as names).
    Supports Debian / RHEL / Fedora / SUSE / openEuler.
    """
    pkg_str = " ".join(packages)

    cmd = f"""
detect_os() {{
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        if [ -n "$ID_LIKE" ]; then
            echo "$ID_LIKE"
        else
            echo "$ID"
        fi
    else
        echo "$(uname -s)"
    fi
}}

OS=$(detect_os)

ensure_repo() {{
    if echo "$OS" | grep -qi "debian"; then
        sed -i 's/archive.ubuntu.com/mirrors.yunsilicon.com/g' /etc/apt/sources.list || true
        sed -i 's/security.ubuntu.com/mirrors.yunsilicon.com/g' /etc/apt/sources.list || true
        apt-get update -y || true

    elif echo "$OS" | grep -Ei "rhel|centos"; then
        if grep -q 'VERSION_ID="7"' /etc/os-release 2>/dev/null; then
            curl -s -o /etc/yum.repos.d/centos.repo http://mirrors.yunsilicon.com/yum.repos.d/centos7.9.repo || true
            curl -s -o /etc/yum.repos.d/epel.repo http://mirrors.yunsilicon.com/yum.repos.d/epel7.repo || true
        fi
        yum clean all || true
        yum makecache || true

    elif echo "$OS" | grep -qi "fedora"; then
        dnf makecache || true

    elif echo "$OS" | grep -qi "suse"; then
        zypper refresh || true

    elif echo "$OS" | grep -qi "openeuler"; then
        # openEuler 22+ 使用 dnf
        dnf makecache || true

    fi
}}

ensure_packages() {{
    MISSING=()
    for pkg in {pkg_str}; do
        if ! command -v $pkg >/dev/null 2>&1; then
            MISSING+=($pkg)
        fi
    done

    if [ ${{#MISSING[@]}} -eq 0 ]; then
        echo "All packages already installed"
        return
    fi

    echo "Installing packages: ${{MISSING[@]}}"

    if echo "$OS" | grep -qi "debian"; then
        apt-get install -y ${{MISSING[@]}}

    elif echo "$OS" | grep -Ei "rhel|centos"; then
        yum install -y ${{MISSING[@]}}

    elif echo "$OS" | grep -qi "fedora"; then
        dnf install -y ${{MISSING[@]}}

    elif echo "$OS" | grep -qi "suse"; then
        zypper install -y ${{MISSING[@]}}

    elif echo "$OS" | grep -qi "openeuler"; then
        dnf install -y ${{MISSING[@]}}

    else
        echo "Unsupported distro: $OS"
        exit 1
    fi
}}

ensure_repo
ensure_packages
"""  # noqa

    LOG.info(f"Ensuring repo and packages on {host}: {packages}")
    await ssh_execute_async(host, cmd, user, pwd)


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


async def get_mellanox_nics(ip: str, user: str, password: str) -> List[Dict]:
    """
    Get Mellanox NIC info from remote server, return in the same format as parse_nics_info.
    """

    def simplify_mlx_product_name(raw_name: str) -> str:
        model_match = re.search(r'ConnectX-\d+', raw_name)
        model = model_match.group(0) if model_match else ""

        speed_match = re.search(r'(\d+)GbE', raw_name)
        speed = f"{speed_match.group(1)}G" if speed_match else ""

        return " ".join(filter(None, [model, speed]))

    pci_cmd = "lspci -n -d 15b3: | awk '{print $1}'"
    pci_res = await ssh_execute_async(ip, pci_cmd, user, password)
    pci_list = pci_res.splitlines()

    devices = []

    for pci in pci_list:
        pci = pci.strip()
        if not pci:
            continue

        detail_cmd = f"lspci -vvv -s {pci}"
        detail_res = await ssh_execute_async(ip, detail_cmd, user, password)

        current = {"bdf": pci}
        for line in detail_res.splitlines():
            line = line.strip()
            if line.startswith("Product Name:"):
                current["Product Name"] = line.replace("Product Name:", "").strip()
            elif "[PN]" in line and "Part number:" in line:
                current["Part number"] = line.split(":")[-1].strip()
            elif "[SN]" in line and "Serial number:" in line:
                current["Serial number"] = line.split(":")[-1].strip()

        iface_cmd = f"basename $(readlink -f /sys/bus/pci/devices/0000:{pci}/net/* 2>/dev/null)"
        iface_res = await ssh_execute_async(ip, iface_cmd, user, password)
        iface_list = iface_res.splitlines()

        nic_info = []
        for iface in iface_list:
            iface = iface.strip()
            if not iface:
                continue
            mac_cmd = f"cat /sys/class/net/{iface}/address"
            mac_res = await ssh_execute_async(ip, mac_cmd, user, password)
            mac = mac_res.strip()
            nic_info.append({
                "bdf": pci,
                "iface": iface,
                "mac": mac
            })

        if all(k in current for k in ("Product Name", "Part number", "Serial number")):
            devices.append({**current, "nic_info": nic_info})

    counter = defaultdict(list)
    for d in devices:
        key = (d["Product Name"], d["Part number"], d["Serial number"])
        counter[key].append(d)

    result = []
    for key, dev_list in counter.items():
        prod_name, part_num, sn = key
        nic_infos = []
        for d in dev_list:
            nic_infos.extend(d["nic_info"])
        result.append({
            "sn": sn,
            "type": simplify_mlx_product_name(prod_name),
            "nic_info": nic_infos
        })

    return result


def parse_bdf_partnum(output: str) -> Dict[str, Dict[str, str]]:
    """
    Parse BDF → {pn, sn} from 'yuncli fw --fru_info' output.
    Supports:
      - Single BDF:  BDF:0000:87:00.0:
      - Multiple BDFs: Multihost BDFs:0000:41:00.0,0000:c1:00.0:
    Strips PCI domain (first 4 hex digits) to get e.g., "87:00.0".
    """
    result: Dict[str, Dict[str, str]] = {}
    current_bdfs: list[str] = []

    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue

        # 1. Detect single BDF
        if line.startswith("BDF:") and line.endswith(":"):
            raw_bdf = line.replace("BDF:", "").rstrip(":")
            parts = raw_bdf.split(":")
            if len(parts) == 3 and parts[0] == "0000":
                bdf = ":".join(parts[1:])  # "87:00.0"
            else:
                bdf = raw_bdf
            current_bdfs = [bdf]
            for b in current_bdfs:
                result.setdefault(b, {})
            continue

        # 2. Detect multiple BDFs (Multihost)
        if line.startswith("Multihost BDFs:") and line.endswith(":"):
            raw = line.replace("Multihost BDFs:", "").rstrip(":")
            bdfs = []
            for raw_bdf in raw.split(","):
                raw_bdf = raw_bdf.strip()
                parts = raw_bdf.split(":")
                if len(parts) == 3 and parts[0] == "0000":
                    bdf = ":".join(parts[1:])
                else:
                    bdf = raw_bdf
                bdfs.append(bdf)
                result.setdefault(bdf, {})
            current_bdfs = bdfs
            continue

        # 3. Product Part Number
        if "Product Part Number" in line and ":" in line:
            value = line.split(":", 1)[1].strip()
            for bdf in current_bdfs:
                result[bdf]["pn"] = value
            continue

        # 4. Product Serial
        if "Product Serial" in line and ":" in line:
            value = line.split(":", 1)[1].strip()
            for bdf in current_bdfs:
                result[bdf]["sn"] = value
            continue

    return result


def parse_bdf_mac(output: str) -> Dict[str, List[dict]]:
    """
    Parse `yuncli mac -r` output into {root_bdf: [{"bdf": bdf_with_func, "mac": mac}, ...]}.
    Supports:
      - Single BDF:  BDF:0000:87:00.0:
      - Multiple BDFs: Multihost BDFs:0000:41:00.0,0000:c1:00.0:
    For Multihost BDFs, MACs are evenly distributed across BDFs.
    """
    result: Dict[str, List[dict]] = {}
    current_bdfs: List[str] = []
    macs_buffer: List[str] = []

    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue

        # 1. Detect single BDF
        m_single = re.match(r"BDF:([0-9a-fA-F:.]+):", line)
        if m_single:
            # flush previous buffer if any
            if current_bdfs and macs_buffer:
                result = _assign_macs_to_bdfs(result, current_bdfs, macs_buffer)
            raw = m_single.group(1)
            if raw.startswith("0000:"):
                raw = raw[5:]
            current_bdfs = [raw]
            result.setdefault(raw, [])
            macs_buffer = []
            continue

        # 2. Detect multiple BDFs (Multihost)
        if line.startswith("Multihost BDFs:") and line.endswith(":"):
            if current_bdfs and macs_buffer:
                result = _assign_macs_to_bdfs(result, current_bdfs, macs_buffer)
            raw = line.replace("Multihost BDFs:", "").rstrip(":")
            bdfs = []
            for r in raw.split(","):
                r = r.strip()
                if r.startswith("0000:"):
                    r = r[5:]
                bdfs.append(r)
                result.setdefault(r, [])
            current_bdfs = bdfs
            macs_buffer = []
            continue

        # 3. Skip header like "Index Mac Address"
        if line.lower().startswith("index"):
            continue

        # 4. Collect MAC lines
        parts = line.split()
        if len(parts) == 2:
            macs_buffer.append(parts[1].lower())

    # flush remaining buffer
    if current_bdfs and macs_buffer:
        result = _assign_macs_to_bdfs(result, current_bdfs, macs_buffer)

    return result


def _assign_macs_to_bdfs(result: Dict[str, List[dict]], 
                         bdfs: List[str], 
                         macs: List[str]) -> Dict[str, List[dict]]:
    """
    Evenly distribute MACs across BDFs. func numbering starts from 0 per BDF.
    """
    n_bdfs = len(bdfs)
    for idx, mac in enumerate(macs):
        bdf_idx = idx % n_bdfs
        func_idx = idx // n_bdfs
        root_bdf = bdfs[bdf_idx]
        base = root_bdf[:-1]
        full_bdf = f"{base}{func_idx}"
        result[root_bdf].append({
            "bdf": full_bdf,
            "mac": mac
        })
    return result


async def get_boot_entries(host_ip, user, pwd):
    efiboot_output = (await ssh_execute_async(host_ip, "efibootmgr -v", user, pwd)).splitlines()
    lsblk_output = (await ssh_execute_async(
        host_ip, "lsblk -rno NAME,PKNAME,PARTUUID", user, pwd)).splitlines()

    uuid_to_disk = {}
    for line in lsblk_output:
        parts = line.strip().split()
        if len(parts) == 3:
            name, parent, partuuid = parts
            partuuid = partuuid.lower() if partuuid != "-" else ""
            uuid_to_disk[partuuid] = parent or name

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


async def collect_device_info(ip, user, password):
    server_sn = await ssh_execute_async(
        ip, "cat /sys/class/dmi/id/product_serial", user, password, False)
    server_vendor = await ssh_execute_async(ip, "cat /sys/class/dmi/id/sys_vendor", user, password)
    server_product = await ssh_execute_async(
        ip, "cat /sys/class/dmi/id/product_name", user, password)

    cpu_cmd = (
        "lscpu | awk -F\":\" "
        "'/Architecture:|Vendor ID:|Model name:/ "
        "{gsub(/^[ \\t]+/, \"\", $2); print $2}'"
    )
    cpu_infos = (await ssh_execute_async(ip, cpu_cmd, user, password)).strip().split("\n")

    route_cmd = (
        f"ip route get {COMMON_SERVER} | head -1 | "
        "awk '{for(i=1;i<=NF;i++) if($i==\"dev\") print $(i+1)}'"
    )
    iface_name = await ssh_execute_async(ip, route_cmd, user, password)
    iface_mac = (await ssh_execute_async(
        ip, f"cat /sys/class/net/{iface_name}/address", user, password)).strip()

    gateway = (await ssh_execute_async(
        ip, "ip route | awk '/default/ {print $3}'", user, password)).strip()

    return {
        "sn": server_sn,
        "mac": iface_mac,
        "gateway": gateway,
        "vendor": server_vendor,
        "product": server_product,
        "arch": cpu_infos[0],
        "cpu_vendor": cpu_infos[1],
        "cpu_mode": cpu_infos[2]
    }


async def collect_nic_info(ip: str, user: str, password: str, check=True) -> list:
    """
    Collect NIC info from remote server.
    - Parse PCI info
    - Parse FRU part number & serial
    - Parse MACs
    - Merge into unified structure with type/mac/iface
    """
    # PCI info
    pci_cmd = (
        "lspci -d 1f67: -vvv | awk '/Ethernet controller/ {print} "
        "/Vital Product Data/ {print; for(i=0;i<5;i++){getline; print}}'"
    )
    pci_res = await ssh_execute_async(ip, pci_cmd, user, password)
    nics = parse_nics_info(pci_res)

    # FRU info
    part_num_cmd = 'yuncli fw --fru_info'
    part_num_res = await ssh_execute_async(ip, part_num_cmd, user, password, check)
    partnums = parse_bdf_partnum(part_num_res)

    # MAC info
    mac_res = await ssh_execute_async(ip, "yuncli mac -r", user, password, check)
    macs = parse_bdf_mac(mac_res)

    # Build nics_list
    nics_map: dict[str, dict] = {}

    for root_bdf, funcs in macs.items():
        part_info = partnums.get(root_bdf, {})
        pn = part_info.get("pn", "")
        sn = part_info.get("sn", "")
        nic_type = PRODUCT_PART_NUMBER_DICT.get(pn, "")

        nic_info_list = [{"bdf": f["bdf"], "mac": f["mac"]} for f in funcs]

        if sn in nics_map:
            # SN 已存在，则合并 nic_info
            nics_map[sn]["nic_info"].extend(nic_info_list)
        else:
            # 新 SN，创建条目
            nics_map[sn] = {
                "sn": sn,
                "type": nic_type,
                "nic_info": nic_info_list
            }

    merged = [nics_map.get(nic.get("sn"), nic) for nic in nics]
    # Add nics_list entries not in nics
    existing_sn = {nic.get("sn") for nic in nics}
    merged.extend(nic for sn, nic in nics_map.items() if sn not in existing_sn)

    # Remote iface mapping
    map_cmd = (
        "for i in /sys/class/net/*/address; do "
        "echo \"$(basename $(dirname $i)) $(cat $i)\"; "
        "done"
    )
    out = await ssh_execute_async(ip, map_cmd, user, password)
    remote_map = {}
    for line in out.splitlines():
        line = line.strip().strip('\'"')
        if not line:
            continue
        parts = line.split()
        if len(parts) >= 2:
            iface, mac = parts[0], parts[1].lower()
            remote_map[mac] = iface

    # Enrich merged nics with iface
    for nic in merged:
        for info in nic["nic_info"]:
            mac = info.get("mac")
            if mac:
                iface = remote_map.get(mac.lower())
                if iface:
                    info["iface"] = iface

    mellanox_nics = await get_mellanox_nics(ip, user, password)
    merged.extend(mellanox_nics)
    return merged


async def update_automatic_async(ip, user, password):
    device_info = await collect_device_info(ip, user, password)
    nics = await collect_nic_info(ip, user, password, False)
    return device_info, nics


def create_mcr_task(server_id, option):
    """Create a new task and store in DB. Keep only the latest 10 tasks per server."""
    task_id = str(uuid4())
    now = datetime.now().isoformat()

    task_info = {
        "id": task_id,
        "server_id": server_id,
        "status": "pending",
        "stage": "waiting",
        "detail": "",
        "timestamp": now,
        "mcr": "",
        "option": option
    }

    db.insert(TASK_POOL_COLLECTION, task_info)

    tasks = db.find(TASK_POOL_COLLECTION, {"server_id": server_id, "option": option})

    if len(tasks) > 10:
        tasks_sorted = sorted(tasks, key=lambda x: x.get("timestamp", ""))

        remove_count = len(tasks) - 10
        old_tasks = tasks_sorted[:remove_count]

        for t in old_tasks:
            db.delete(TASK_POOL_COLLECTION, {"id": t["id"]})

    return task_id


def update_task(task_id, **kwargs):
    """Update task info in DB."""
    try:
        task = db.find_one(TASK_POOL_COLLECTION, {"id": task_id})
    except Exception:
        return
    for k, v in kwargs.items():
        task[k] = v
    db.update(TASK_POOL_COLLECTION, {"id": task_id}, task)


async def fetch_mcr_package(task_id: str, host: str, user: str, pwd: str, path: str):
    """
    Fetch and prepare MCR package on remote server:
      - Create temp dir
      - Check if package exists
      - Ensure sshpass installed
      - Download package if missing
      - Extract package if not extracted yet

    Returns: (temp_dir, pkg_path, root_dir)
    """
    package_name = os.path.basename(path)
    root_name = package_name.replace(".tar.gz", "")
    temp_dir = f"/tmp/tmp_{root_name}"
    pkg_path = os.path.join(temp_dir, package_name)
    root_dir = os.path.join(temp_dir, root_name)

    # Step 1: Create temp directory
    LOG.info(f"[{task_id}] Step 1: Creating temp directory")
    update_task(task_id, status="running", stage="getting_mcr",
                detail="Creating temp directory", mcr=path)

    mkdir_cmd = f"mkdir -p {temp_dir}"
    await ssh_execute_async(host, mkdir_cmd, user, pwd)
    LOG.info(f"[{task_id}] Temp directory created: {temp_dir}")

    # Step 2: Check if package already exists
    check_pkg = f"test -f {pkg_path} && echo 'exists' || echo 'not_exists'"
    pkg_exists = (await ssh_execute_async(host, check_pkg, user, pwd)).strip() == "exists"

    if not pkg_exists:
        # Step 2-1: Ensure sshpass exists
        try:
            check_sshpass_cmd = "command -v sshpass >/dev/null 2>&1"
            await ssh_execute_async(host, check_sshpass_cmd, user, pwd)
        except Exception:
            update_task(task_id, detail="installing sshpass")
            await ensure_packages_installed(host, user, pwd, ["sshpass", "ipmitool"])

        # Step 2-2: Download package
        update_task(task_id, detail="Downloading MCR package from common server")
        LOG.info(f"[{task_id}] Downloading MCR {package_name} from {COMMON_SERVER}")

        download_cmd = (
            f"sshpass -p '{COMMON_USER_PASSWORD}' scp -o StrictHostKeyChecking=no "
            f"{COMMON_USER}@{COMMON_SERVER}:{path} {temp_dir}"
        )
        await ssh_execute_async(host, download_cmd, user, pwd)
        LOG.info(f"[{task_id}] MCR package downloaded: {package_name}")

    # Step 3: Check if root directory already exists (means extracted)
    check_root = f"test -d {root_dir} && echo 'exists' || echo 'not_exists'"
    root_exists = (await ssh_execute_async(host, check_root, user, pwd)).strip() == "exists"

    if not root_exists:
        update_task(task_id, detail="Extracting package")
        LOG.info(f"[{task_id}] Extracting package {package_name}")

        extract_cmd = f"tar -zxvf {pkg_path} -C {temp_dir}"
        await ssh_execute_async(host, extract_cmd, user, pwd)
        LOG.info(f"[{task_id}] Package extracted to {temp_dir}")

    return root_dir


def parse_bdf_from_upgrade(upgrade_output: str):
    LOG.info("Parsing BDF list from firmware upgrade output...")

    bdf_list = []

    # 1. Match pattern: |--[87:00.0]
    pattern1 = r"\|\--\[[0-9a-fA-F]{2}:[0-9a-fA-F]{2}\.[0-9]\]"
    matches1 = re.findall(pattern1, upgrade_output)
    if matches1:
        bdf_list.extend([m.replace("|--[", "").replace("]", "") for m in matches1])

    # 2. If not found, match BDF:0000:xx:xx.x
    if not bdf_list:
        pattern2 = r"BDF:0000:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}\.[0-9]"
        matches2 = re.findall(pattern2, upgrade_output)
        if matches2:
            # Extract last two parts, e.g. 0000:87:00.0 → 87:00.0
            bdf_list.extend([m.split(":")[2] + ":" + m.split(":")[3] for m in matches2])

    # 3. If still not found, match device: xx:xx.x
    if not bdf_list:
        pattern3 = r"device:\s+([0-9a-fA-F]{2}:[0-9a-fA-F]{2}\.[0-9])"
        matches3 = re.findall(pattern3, upgrade_output)
        if matches3:
            bdf_list.extend(matches3)

    # Remove duplicates
    bdf_list = sorted(list(set(bdf_list)))

    # 4. If still empty, fallback to lspci Yunsilicon search
    if not bdf_list:
        LOG.warning("No BDF found in upgrade output.")
        LOG.info("Trying to search Yunsilicon devices via lspci...")

        try:
            lspci_output = subprocess.check_output(["lspci"], universal_newlines=True)
            pattern4 = r"^([0-9a-fA-F]{2}:[0-9a-fA-F]{2}\.[0-9]).*Yunsilicon"
            matches4 = re.findall(pattern4, lspci_output, re.MULTILINE)
            if matches4:
                bdf_list.append(matches4[0])
        except Exception:
            LOG.exception("Failed to execute lspci for fallback scanning.")

    # Final result
    if not bdf_list:
        LOG.warning("No valid BDF found.")
    else:
        LOG.info("Detected BDF list: %s", " ".join(bdf_list))

    return bdf_list


async def wait_for_server_reboot(host: str, timeout: int = 900, 
                                 interval: int = 10, initial_delay: int = 30):
    """
    Wait for a server to reboot by pinging it periodically.

    :param host: IP or hostname of the server
    :param timeout: Maximum wait time in seconds (default 900 = 15 minutes)
    :param interval: Ping interval in seconds
    :param initial_delay: Wait this many seconds before the first ping (default 10s)
    :return: True if server is up, False if timeout
    """
    LOG.info(f"Waiting for server {host} to reboot (timeout {timeout}s)...")

    # Wait initial delay before first ping
    await asyncio.sleep(initial_delay)

    end_time = asyncio.get_event_loop().time() + timeout

    while True:
        if asyncio.get_event_loop().time() > end_time:
            LOG.warning(f"Timeout reached while waiting for {host} to reboot")
            return False

        # Run ping asynchronously
        proc = await asyncio.create_subprocess_exec(
            "ping", "-c", "1", "-W", "1", host,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        returncode = await proc.wait()

        if returncode == 0:
            LOG.info(f"Server {host} is back online")
            return True
        else:
            LOG.debug(f"Server {host} not reachable yet, waiting {interval}s...")
            await asyncio.sleep(interval)


async def run_mcr_update_task(task_id: str, host: str, user: str, pwd: str, ipmi: str,
                              data: common_schemas.MCRRequest, aidpu: bool = False):
    try:
        # Step Group 1: Fetch MCR Package
        root_dir = await fetch_mcr_package(task_id, host, user, pwd, data.path)

        if data.update_options == "fw":
            # Step Group 2: Upgrade Fw
            update_task(task_id, stage="upgrading_fw", detail="Upgrading fw hw")
            LOG.info(f"[{task_id}] run yun_upgrade.sh in {root_dir}/fw_hw/")

            uninstall_cmd = (f"cd {root_dir}/fw_hw/ && chmod +x yun_upgrade.sh"
                             " && ./yun_upgrade.sh 2>&1")
            upgrade_result = await ssh_execute_async(host, uninstall_cmd, user, pwd)
            LOG.info(f"[{task_id}] fw hw upgraded")

            bdf_list = parse_bdf_from_upgrade(upgrade_result)
            update_task(task_id, stage="erasing_bdf", detail=f"Erasing bdfs {bdf_list}")
            for bdf in bdf_list:
                erase_cmd = (f'{root_dir}/fw_hw/tools/yuncli/yuncli fw -d "{bdf}" --config erase')
                await ssh_execute_async(host, erase_cmd, user, pwd)
            LOG.info(f"[{task_id}]All BDFs in {bdf_list} have been successfully erased.")

            update_task(task_id, stage="reboot", detail="The server is restarting")
            ipmi_power_action(ipmi, "reset")

            success = await wait_for_server_reboot(host)
            if success:
                update_task(task_id, status="finished", detail="MCR update completed")
                LOG.info(f"[{task_id}] Reset Fw task finished successfully")
            else:
                LOG.error(f"{host} did not come online within timeout")
                update_task(task_id, status="reboot_timeout", detail="Server restart timeout")

        else:
            # Step Group 2: Uninstall Old MCR
            # update_task(task_id, stage="uninstalling_mcr", detail="Uninstalling old MCR")
            # LOG.info(f"[{task_id}] Uninstalling old MCR in {root_dir}")

            # extra_args = " --ovs-dpdk --spdk" if aidpu else ""
            # uninstall_cmd = f"cd {root_dir} && ./uninstall.sh --force{extra_args}"

            # await ssh_execute_async(host, uninstall_cmd, user, pwd)
            # LOG.info(f"[{task_id}] Old MCR uninstalled")

            # Step Group 3: Install New MCR
            update_task(task_id, stage="installing_mcr", detail="Installing new MCR")
            LOG.info(f"[{task_id}] Installing new MCR with option: {data.update_options}")

            if aidpu:
                install_cmd = (f'cd {root_dir} &&./install.sh --ovs-dpdk --spdk '
                               '--yun-upgrade-option "--dpu-blk-oprom --best-try" --dpuagent')
            else:
                if data.update_options == "all":
                    install_cmd = f"cd {root_dir} && ./install.sh --force"
                elif data.update_options == "no-fw":
                    install_cmd = f"cd {root_dir} && ./install.sh --force --no-fw-update"
                else:
                    raise Exception("Invalid update option")

            await ssh_execute_async(host, install_cmd, user, pwd)
            LOG.info(f"[{task_id}] New MCR installed successfully")

            if aidpu:
                update_task(task_id, status="finished",
                            detail="MCR update completed (Note: A cold reboot is required)")
            else:
                update_task(task_id, stage="reboot",
                            detail="The server is undergoing a cold restart")
                ipmi_power_action(ipmi, "cycle")

                success = await wait_for_server_reboot(host)
                if success:
                    update_task(task_id, status="finished", detail="MCR update completed")
                    LOG.info(f"[{task_id}] Reset Fw task finished successfully")
                else:
                    LOG.error(f"{host} did not come online within timeout")
                    update_task(task_id, status="reboot_timeout", detail="Server restart timeout")

            LOG.info(f"[{task_id}] MCR update task finished successfully")

    except Exception as e:
        update_task(task_id, status="failed", detail=str(e))
