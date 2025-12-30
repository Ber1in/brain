# Copyright (C) 2021 - 2025, Shanghai Yunsilicon Technology Co., Ltd.
# All rights reserved.

import asyncio
from collections import OrderedDict, defaultdict
from datetime import datetime
import logging
import os
import re
import subprocess
from typing import Any, Dict, List
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


def parse_ip_br_output(output: str) -> Dict[str, Dict[str, List[str]]]:
    """
    Parse the output of ip -br addr show command

    Args:
        output: Output string from ip -br addr show command

    Returns:
        Dict[str, Dict[str, List[str]]]: interface name -> {'ipv4': [], 'ipv6': []}
        Only includes interfaces that have at least one IP address (IPv4 or IPv6)
    """
    interfaces = {}

    for line in output.strip().split('\n'):
        if not line:
            continue

        parts = line.split()
        if len(parts) < 2:
            continue

        ifname = parts[0]  # Interface name
        ipv4_addresses = []
        ipv6_addresses = []

        # Extract IP addresses
        for part in parts[2:]:  # Skip interface name and status
            # IPv4 address pattern
            if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d+$', part):
                ipv4_addresses.append(part)
            # IPv6 address pattern (contains colon)
            elif ':' in part:
                ipv6_addresses.append(part)

        # Only record interfaces with IP addresses
        if ipv4_addresses or ipv6_addresses:
            interfaces[ifname] = {
                'ipv4': ipv4_addresses,
                'ipv6': ipv6_addresses
            }

    return interfaces


async def ensure_packages_installed(host: str, user: str, pwd: str, packages: list):
    """
    Ensure packages (interpreted as commands) exist on remote host.
    If not, install corresponding packages (assumed same as names).
    Supports Debian / Ubuntu / Kylin / RHEL / CentOS / Fedora / SUSE / openEuler.
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

ensure_repo() {{
    if echo "$OS" | grep -qiE "debian|ubuntu|kylin.*debian"; then
        # Debian/Ubuntu/Kylin Desktop
        sed -i 's/archive.ubuntu.com/mirrors.yunsilicon.com/g' /etc/apt/sources.list || true
        sed -i 's/security.ubuntu.com/mirrors.yunsilicon.com/g' /etc/apt/sources.list || true
        apt-get update -y || true

    elif echo "$OS" | grep -qiE "rhel|centos|fedora|openeuler|kylin"; then
        # RHEL/CentOS/Fedora/OpenEuler/Kylin Advanced Server
        if grep -q 'VERSION_ID="7"' /etc/os-release 2>/dev/null; then
            rm -rf /etc/yum.repos.d/*
            curl -s -o /etc/yum.repos.d/centos.repo http://mirrors.yunsilicon.com/yum.repos.d/centos7.9.repo || true
            curl -s -o /etc/yum.repos.d/epel.repo http://mirrors.yunsilicon.com/yum.repos.d/epel7.repo || true
        elif grep -q 'VERSION_ID="8"' /etc/os-release 2>/dev/null; then
            rm -rf /etc/yum.repos.d/*
            curl -s -o /etc/yum.repos.d/rhel8.6.repo https://mirrors.yunsilicon.com/yum.repos.d/rhel8.6.repo
            curl -s -o /etc/yum.repos.d/epel8.repo http://mirrors.yunsilicon.com/yum.repos.d/epel8.repo || true
        fi
        yum clean all || true
        yum makecache || true

    elif echo "$OS" | grep -qi "fedora"; then
        dnf makecache || true

    elif echo "$OS" | grep -qi "suse"; then
        zypper refresh || true
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
        return 0
    fi

    echo "Missing packages: ${{MISSING[@]}}"

    OS=$(detect_os)
    ensure_repo

    echo "Installing packages: ${{MISSING[@]}}"

    if echo "$OS" | grep -qiE "debian|ubuntu|kylin.*debian"; then
        apt-get install -y ${{MISSING[@]}}

    elif echo "$OS" | grep -qiE "rhel|centos|fedora|openeuler|kylin"; then
        yum install -y ${{MISSING[@]}} || dnf install -y ${{MISSING[@]}}

    elif echo "$OS" | grep -qi "suse"; then
        zypper install -y ${{MISSING[@]}}

    else
        echo "Unsupported distro: $OS"
        exit 1
    fi
}}

ensure_packages
"""  # noqa

    LOG.info(f"Ensuring repo and packages on {host}: {packages}")
    await ssh_execute_async(host, cmd, user, pwd)


async def ensure_server_active(host, user, password, services: list):
    await ssh_execute_async(host, f"systemctl start {' '.join(services)}", user, password)


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


def simplify_mlx_product_name(raw_name: str) -> str:
    model_match = re.search(r'ConnectX-\d+', raw_name)
    model = model_match.group(0) if model_match else ""

    speed_match = re.search(r'(\d+)GbE', raw_name)
    speed = f"{speed_match.group(1)}G" if speed_match else ""

    return " ".join(filter(None, [model, speed]))


async def get_nics(
    ip: str,
    user: str,
    password: str,
    vendor_id: str,
    product_infos: dict = None
) -> List[Dict]:
    """
    Get NIC info from remote server, return in the same format as parse_nics_info.
    Ensures that devices without SN/Product Name are still returned.
    :param vendor_id: PCI vendor ID (e.g., '1f67' for Yunsilicon, '15b3' for Mellanox)
    """
    pci_cmd = f"lspci -Dn -d {vendor_id}: | awk '{{print $1}}'"
    pci_res = await ssh_execute_async(ip, pci_cmd, user, password)
    pci_list = [pci.strip() for pci in pci_res.splitlines() if pci.strip()]

    product_infos = product_infos or {}
    devices = []

    semaphore = asyncio.Semaphore(5) 

    async def fetch_pci_info(pci: str) -> Dict:
        async with semaphore:
            detail_cmd = f"lspci -vvv -s {pci}"
            detail_res = await ssh_execute_async(ip, detail_cmd, user, password)

            current = {"bdf": pci, "type": "", "sn": "", "pcie_width": ""}

            for line in detail_res.splitlines():
                line = line.strip()
                if line.startswith("Product Name:"):
                    current["type"] = line.replace("Product Name:", "").strip()
                elif "[SN]" in line and "Serial number:" in line:
                    current["sn"] = line.split(":")[-1].strip()

                elif "LnkSta:" in line and "Width" in line:
                    import re
                    match = re.search(r'Width\s+(x\d+)', line)
                    if match:
                        current["pcie_width"] = match.group(1)

            if current["pcie_width"] == "":
                try:
                    width_cmd = f"cat /sys/bus/pci/devices/{pci}/current_link_width 2>/dev/null"
                    width_res = await ssh_execute_async(ip, width_cmd, user, password, False)
                    sys_width = width_res.strip()
                    if sys_width.isdigit():
                        current["pcie_width"] = f"x{sys_width}"
                except Exception:
                    pass

            nic_info = []

            if vendor_id.lower() == "1f67":
                pf = await ssh_execute_async(
                    ip, f"test -e /sys/bus/pci/devices/{pci}/vpd && echo 1 || echo 0",
                    user, password)
                if pf.strip() == "0":
                    return None

            cmd = f"ls /sys/bus/pci/devices/{pci}/net | grep -v '_h'"
            ifaces = (await ssh_execute_async(ip, cmd, user, password, False)).strip().splitlines()

            if ifaces:
                for iface in ifaces:
                    mac = (await ssh_execute_async(
                        ip, f"ethtool -P {iface}", user, password)).strip().split()[-1]
                    nic_info.append({"bdf": pci, "iface": iface, "mac": mac})
            else:
                nic_info.append({"bdf": pci, "iface": "", "mac": ""})

            return {**current, "nic_info": nic_info}

    pci_tasks = [fetch_pci_info(pci) for pci in pci_list]
    pci_results = await asyncio.gather(*pci_tasks)

    devices = [res for res in pci_results if res]

    for dev in devices:
        if vendor_id.lower() == "1f67":
            for nic_info in dev["nic_info"]:
                product_info = product_infos.get(nic_info["bdf"])
                if product_info:
                    dev["type"] = PRODUCT_PART_NUMBER_DICT.get(
                        product_info["pn"],
                        product_info["pn"]
                    )
                    dev["sn"] = product_info.get("sn")
                    break
        elif vendor_id.lower() == "15b3":
            dev["type"] = simplify_mlx_product_name(dev.get("type"))

    merged_pf = OrderedDict()

    for dev in devices:
        cmd = (f"test -L /sys/bus/pci/devices/{dev['bdf']}/physfn "
               f"&& readlink -f /sys/bus/pci/devices/{dev['bdf']}/physfn | xargs basename")
        res = await ssh_execute_async(ip, cmd, user, password, False)

        key = res.strip() or dev["bdf"]

        pf = merged_pf.setdefault(key, {"type": "", "sn": "", "pcie_width": "", "nic_info": []})

        if key == dev["bdf"]:
            pf.update({"type": dev.get("type", ""), "sn": dev.get("sn", ""),
                       "pcie_width": dev.get("pcie_width", "")})

        pf["nic_info"].extend(dev.get("nic_info", []))

    pf_list = list(merged_pf.values())

    merged_sn = OrderedDict()

    for item in pf_list:
        sn_key = item.get("sn") or f"nosn_{id(item)}"

        if sn_key not in merged_sn:
            merged_sn[sn_key] = {
                "type": item.get("type", ""),
                "sn": item.get("sn", ""),
                "pcie_width": item.get("pcie_width", ""),
                "nic_info": []
            }

        merged_sn[sn_key]["nic_info"].extend(item.get("nic_info", []))

    return list(merged_sn.values())


def parse_bdf_partnum(output: str) -> Dict[str, Dict[str, str]]:
    """
    Parse BDF → {pn, sn} from 'yuncli fw --fru_info' output.
    Supports:
      - Single BDF:  BDF:0000:87:00.0:
      - Multiple BDFs: Multihost BDFs:0000:41:00.0,0000:c1:00.0:
    Keeps full PCI BDF including domain (e.g. 0000:87:00.0).
    """
    result: Dict[str, Dict[str, str]] = {}
    current_bdfs: list[str] = []

    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue

        # 1. Detect single BDF
        if line.startswith("BDF:") and line.endswith(":"):
            bdf = line.replace("BDF:", "").rstrip(":")
            current_bdfs = [bdf]
            for b in current_bdfs:
                result.setdefault(b, {})
            continue

        # 2. Detect multiple BDFs (Multihost)
        if line.startswith("Multihost BDFs:") and line.endswith(":"):
            raw = line.replace("Multihost BDFs:", "").rstrip(":")
            bdfs = []
            for bdf in raw.split(","):
                bdf = bdf.strip()
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


def parse_bdf_mac(output: str) -> List[dict]:
    """
    Parse `yuncli mac -r` output into a list of dicts:
    [{"bdf": bdf_with_domain, "mac": mac}, ...].

    Supports:
      - Single BDF:  BDF:0000:87:00.0:
      - Multiple BDFs: Multihost BDFs:0000:41:00.0,0000:c1:00.0:

    For Multihost BDFs, MACs are evenly distributed across BDFs.
    Keeps full PCI BDF including domain.
    """
    result: List[dict] = []
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
                result.extend(_assign_macs_to_bdfs(current_bdfs, macs_buffer))

            raw = m_single.group(1)   # keep full BDF, e.g. 0000:87:00.0
            current_bdfs = [raw]
            macs_buffer = []
            continue

        # 2. Detect multiple BDFs (Multihost)
        if line.startswith("Multihost BDFs:") and line.endswith(":"):
            if current_bdfs and macs_buffer:
                result.extend(_assign_macs_to_bdfs(current_bdfs, macs_buffer))

            raw = line.replace("Multihost BDFs:", "").rstrip(":")
            current_bdfs = [bdf.strip() for bdf in raw.split(",")]
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
        result.extend(_assign_macs_to_bdfs(current_bdfs, macs_buffer))

    return result


def _assign_macs_to_bdfs(bdfs: List[str], macs: List[str]) -> List[dict]:
    """
    Evenly distribute MACs across BDFs. func numbering starts from 0 per BDF.
    Returns a flat list of dicts: [{"bdf": ..., "mac": ...}, ...]
    """
    assigned: List[dict] = []
    n_bdfs = len(bdfs)
    for idx, mac in enumerate(macs):
        bdf_idx = idx % n_bdfs
        func_idx = idx // n_bdfs
        root_bdf = bdfs[bdf_idx]
        base = root_bdf[:-1]
        full_bdf = f"{base}{func_idx}"
        assigned.append({
            "bdf": full_bdf,
            "mac": mac
        })
    return assigned


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


async def ipmi_power_action(bmcip: str, action: str, host: str, user: str, pwd: str):
    """Execute IPMI power action via ipmitool command"""
    LOG.info(f"Executing IPMI {action} on BMC {bmcip}")

    if action not in ("cycle", "reset"):
        raise HTTPException(status_code=400, detail=f"Unsupported IPMI action: {action}")

    cmd = ["ipmitool", "-I", "lanplus", "-H", bmcip, "-U", BMC_USER, "-P", BMC_PASS,
           "chassis", "power", action]

    try:
        used_fallback = False

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            failed = result.returncode != 0
            if failed:
                LOG.error(f"IPMI {action} failed on BMC {bmcip} "
                          f"(local ipmitool): {result.stderr.strip()}")
        except subprocess.TimeoutExpired as e:
            LOG.error(f"IPMI {action} timeout on BMC {bmcip} "
                      f"(local ipmitool): {e}")
            failed = True

        if failed:
            try:
                await ssh_execute_async(host, f"ipmitool power {action}", user, pwd)
                used_fallback = True
            except Exception:
                raise HTTPException(status_code=500,
                                    detail=f"IPMI {action} failed")

        if used_fallback:
            LOG.info(f"Successfully executed IPMI {action} on BMC {bmcip} "
                     f"via SSH fallback")
        else:
            LOG.info(f"Successfully executed IPMI {action} on BMC {bmcip} "
                     f"via local ipmitool")

    except Exception as e:
        LOG.error(f"IPMI {action} execution error on BMC {bmcip}: {e}")
        raise HTTPException(status_code=500,
                            detail=f"IPMI {action} execution error: {e}")


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


async def collect_nic_info(ip: str, user: str, password: str) -> list:
    """
    Collect NIC info from remote server.
    - Parse PCI info
    - Parse FRU part number & serial
    - Parse MACs
    - Merge into unified structure with type/mac/iface
    """
    merged = []

    await ensure_packages_installed(ip, user, password, ["ethtool"])
    part_num_cmd = 'yuncli fw --fru_info'
    part_num_res = await ssh_execute_async(ip, part_num_cmd, user, password, False)
    product_infos = parse_bdf_partnum(part_num_res)
    yunsilicon_nics = await get_nics(ip, user, password, "1f67", product_infos)
    mellanox_nics = await get_nics(ip, user, password, "15b3")
    merged = yunsilicon_nics + mellanox_nics
    switchs_map = await collect_switch_info(ip, user, password)

    ipaddress_res = await ssh_execute_async(ip, "ip -br addr show", user, password, False)
    ipaddress_map = parse_ip_br_output(ipaddress_res)

    for nic in merged:
        for nic_info in nic['nic_info']:
            iface = nic_info['iface']
            if iface in switchs_map:
                nic_info.update(switchs_map[iface])

            if iface in ipaddress_map:
                nic_info.update(ipaddress_map[iface])

    return merged


def parse_lldpctl_output(lldpctl_output: str) -> Dict[str, Dict[str, str]]:
    """
    Parse lldpctl output and return a map from interface name to switch info

    Args:
        lldpctl_output: Output string from lldpctl command

    Returns:
        Dict[str, Dict[str, str]]: Mapping from interface name to switch info
        Example: {
            'ens2f0': {'switch': 'H3C-S9850-32H-G', 'port': 'HundredGigabitEthernet 0/27'},
            'enp65s0np0': {'switch': 'RJ-S6580-LAB-YLF025', 'port': 'HundredGigabitEthernet 0/27'}
        }
    """
    interface_map = {}
    current_neighbor = {}

    lines = lldpctl_output.strip().split('\n')

    for line in lines:
        line = line.strip()

        # Skip separator lines and empty lines
        if re.match(r'-{20,}', line) or not line:
            # Save current neighbor to map if valid
            if current_neighbor and 'interface' in current_neighbor:
                interface = current_neighbor['interface']
                # Add switch and port info if available
                switch_info = {
                    'switch': current_neighbor.get('switch', ''),
                    'port': current_neighbor.get('port', '')
                }
                interface_map[interface] = switch_info
                current_neighbor = {}
            continue

        # Check if this is the start of a new neighbor block
        if line.startswith('Interface:'):
            # Save previous neighbor if exists
            if current_neighbor and 'interface' in current_neighbor:
                interface = current_neighbor['interface']
                switch_info = {
                    'switch': current_neighbor.get('switch', ''),
                    'port': current_neighbor.get('port', '')
                }
                interface_map[interface] = switch_info

            # Start new neighbor
            current_neighbor = {}
            # Extract interface name
            match = re.match(r'Interface:\s+([^,]+)', line)
            if match:
                current_neighbor['interface'] = match.group(1).strip()

        # Extract SysName as switch name
        elif line.startswith('SysName:'):
            switch = line.replace('SysName:', '').strip()
            current_neighbor['switch'] = switch

        # Extract PortID
        elif line.startswith('PortID:'):
            portid_line = line.replace('PortID:', '').strip()

            if portid_line.startswith('ifname '):
                current_neighbor['port'] = portid_line[7:]
            else:
                current_neighbor['port'] = portid_line

    # Add the last neighbor to map
    if current_neighbor and 'interface' in current_neighbor:
        interface = current_neighbor['interface']
        switch_info = {
            'switch': current_neighbor.get('switch', ''),
            'port': current_neighbor.get('port', '')
        }
        interface_map[interface] = switch_info

    return interface_map


async def collect_switch_info(ip, user, password):
    try:
        await ensure_packages_installed(ip, user, password, ["lldpd"])
        await ensure_server_active(ip, user, password, ["lldpd"])
    except Exception:
        LOG.error("The command to ensure package lldpctl failed, "
                  "and switch information could not be retrieved")
    switch_res = await ssh_execute_async(ip, "lldpctl", user, password, False)
    switchs = parse_lldpctl_output(switch_res)
    return switchs


async def update_automatic_async(ip, user, password):
    device_info = await collect_device_info(ip, user, password)
    nics = await collect_nic_info(ip, user, password)
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

    # 1. Match pattern: |--[87:00.0]  (no domain info available)
    pattern1 = r"\|\--\[([0-9a-fA-F]{2}:[0-9a-fA-F]{2}\.[0-9])\]"
    matches1 = re.findall(pattern1, upgrade_output)
    if matches1:
        bdf_list.extend(matches1)

    # 2. Match BDF with optional domain: BDF:0000:87:00.0 or BDF:87:00.0
    if not bdf_list:
        pattern2 = r"BDF:([0-9a-fA-F]{4}:)?([0-9a-fA-F]{2}:[0-9a-fA-F]{2}\.[0-9])"
        matches2 = re.findall(pattern2, upgrade_output)
        if matches2:
            for domain, bdf in matches2:
                # keep full bdf if domain exists
                full_bdf = f"{domain}{bdf}" if domain else bdf
                bdf_list.append(full_bdf)

    # 3. Match device: xx:xx.x (still no domain info)
    if not bdf_list:
        pattern3 = r"device:\s+([0-9a-fA-F]{2}:[0-9a-fA-F]{2}\.[0-9])"
        matches3 = re.findall(pattern3, upgrade_output)
        if matches3:
            bdf_list.extend(matches3)

    # Remove duplicates
    bdf_list = sorted(set(bdf_list))

    # 4. Fallback: scan via lspci (try to keep domain if possible)
    if not bdf_list:
        LOG.warning("No BDF found in upgrade output.")
        LOG.info("Trying to search Yunsilicon devices via lspci...")

        try:
            lspci_output = subprocess.check_output(
                ["lspci", "-D"], universal_newlines=True
            )
            # -D ensures domain is included
            pattern4 = r"^([0-9a-fA-F]{4}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}\.[0-9]).*Yunsilicon"
            matches4 = re.findall(pattern4, lspci_output, re.MULTILINE)
            if matches4:
                bdf_list.extend(matches4)
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
            LOG.info(f"{host} run yun_upgrade.sh in {root_dir}/fw_hw/")

            uninstall_cmd = (f"cd {root_dir}/fw_hw/ && chmod +x yun_upgrade.sh"
                             " && ./yun_upgrade.sh 2>&1")
            upgrade_result = await ssh_execute_async(host, uninstall_cmd, user, pwd)
            LOG.info(f"{host} fw hw upgraded")

            bdf_list = parse_bdf_from_upgrade(upgrade_result)
            update_task(task_id, stage="erasing_bdf", detail=f"Erasing bdfs {bdf_list}")
            for bdf in bdf_list:
                erase_cmd = (f'{root_dir}/fw_hw/tools/yuncli/yuncli fw -d "{bdf}" --config erase')
                await ssh_execute_async(host, erase_cmd, user, pwd)
            LOG.info(f"{host} All BDFs in {bdf_list} have been successfully erased.")

            update_task(task_id, stage="reboot", detail="The server is restarting")
            await ipmi_power_action(ipmi, "reset", host, user, pwd)

            success = await wait_for_server_reboot(host)
            if success:
                update_task(task_id, status="finished", detail="MCR update completed")
                LOG.info(f"{host} Reset Fw task finished successfully")
            else:
                LOG.error(f"{host} did not come online within timeout")
                update_task(task_id, status="reboot_timeout", detail="Server restart timeout")

        else:

            LOG.info(f"{host} Installing new MCR with option: {data.update_options}")

            if aidpu:
                install_cmd = (
                    f'cd {root_dir} && ./install.sh --force --ovs-dpdk --spdk '
                    '--yun-upgrade-option "--dpu-blk-oprom --best-try" --dpuagent'
                )
                uninstall_cmd = f"cd {root_dir} && ./uninstall.sh --force --ovs-dpdk --spdk"
            else:
                if data.update_options == "all":
                    install_cmd = f"cd {root_dir} && ./install.sh --force"
                elif data.update_options == "no-fw":
                    install_cmd = f"cd {root_dir} && ./install.sh --force --no-fw-update"
                else:
                    raise Exception("Invalid update option")

                uninstall_cmd = f"cd {root_dir} && ./uninstall.sh --force"

            # Step Group 2: Install New MCR
            # ---------- first install attempt ----------
            try:
                update_task(task_id, stage="installing_mcr", detail="Installing new MCR")
                LOG.info(f"{host} Trying initial MCR install")
                await ssh_execute_async(host, install_cmd, user, pwd)
                LOG.info(f"{host} New MCR installed successfully (first attempt)")
            except Exception as e:
                LOG.warning(
                    f"{host} Initial MCR install failed, "
                    f"trying uninstall + reinstall: {e}"
                )

                # ---------- uninstall ----------
                try:
                    update_task(task_id, stage="uninstalling_mcr", detail="Uninstalling old MCR")
                    LOG.info(f"{host} Uninstalling old MCR")

                    await ssh_execute_async(host, uninstall_cmd, user, pwd)

                    LOG.info(f"{host} Old MCR uninstalled successfully")
                except Exception as ue:
                    LOG.error(f"{host} Uninstall MCR failed: {ue}")
                    raise

                # ---------- reinstall ----------
                try:
                    update_task(task_id, stage="reinstalling_mcr",
                                detail="Retrying MCR install after uninstall")
                    LOG.info(f"{host} Retrying MCR install after uninstall")
                    await ssh_execute_async(host, install_cmd, user, pwd)
                    LOG.info(f"{host} New MCR installed successfully (after uninstall)")
                except Exception as e:
                    LOG.error(f"{host} MCR install failed after uninstall: {e}")
                    raise

            if aidpu:
                update_task(task_id, status="finished",
                            detail="MCR update completed (Note: A cold reboot is required)")
            else:
                update_task(task_id, stage="reboot",
                            detail="The server is undergoing a cold restart")
                await ipmi_power_action(ipmi, "cycle", host, user, pwd)

                success = await wait_for_server_reboot(host)
                if success:
                    update_task(task_id, status="finished", detail="MCR update completed")
                    LOG.info(f"{host} Reset Fw task finished successfully")
                else:
                    LOG.error(f"{host} did not come online within timeout")
                    update_task(task_id, status="reboot_timeout", detail="Server restart timeout")

            LOG.info(f"{host} MCR update task finished successfully")

    except Exception as e:
        update_task(task_id, status="failed", detail=str(e))


def matches_keyword(device, keyword):
    # 1. Search server name
    hostname = device.get("bmc", {}).get("hostname", "")
    if hostname and keyword in str(hostname).lower():
        return True

    # 2. Search management IP
    device_ip = device.get("device", {}).get("ip", "")
    if device_ip and keyword in device_ip:
        return True

    # 3. Search in notes
    notes = device.get("notes", "")
    if notes and keyword in str(notes).lower():
        return True

    # 4. Search in tags
    tags = device.get("tags", [])
    if tags and any(keyword in str(tag).lower() for tag in tags):
        return True

    # 5. Search in user 
    user_field = device.get("user", "")
    if user_field and keyword in str(user_field).lower() and device.get("time") > 0:
        return True

    # 6. Search in NIC information
    nics = device.get("nics", [])
    for nic in nics:
        # Search NIC type
        nic_type = nic.get("type", "")
        if nic_type and keyword in str(nic_type).lower():
            return True

    return False


def filter_devices(devices: List[Dict[str, Any]], filter_data: Dict[str, Any], 
                   user: str) -> List[Dict[str, Any]]:
    result = []
    now = datetime.now().timestamp()

    filter_tags = filter_data.get("tags") or []
    tag_condition = filter_data.get("tag_filtering_condition", "or")

    filter_nics = filter_data.get("nics") or []
    nic_condition = filter_data.get("nic_filtering_condition", "or")

    only_focus = filter_data.get("only_focus", False)
    search_keyword_value = filter_data.get("search_keyword")

    for device in devices:
        if device.get("time"):
            start = device.get("start", now)
            passed = int(now - start)
            device["time"] = max(device["time"] - passed, 0)

        if filter_data.get("occupyed"):
            if device.get("user") != user or device.get("time", 0) <= 0:
                continue

        if only_focus and user not in device.get("recipients", []):
            continue

        if filter_tags:
            device_tags = set(device.get("tags", []))
            filter_set = set(filter_tags)

            if tag_condition == "or":
                if not device_tags & filter_set:
                    continue
            elif tag_condition == "and":
                if not filter_set.issubset(device_tags):
                    continue

        if filter_nics:
            nic_types = [
                nic.get("type")
                for nic in device.get("nics", [])
                if nic.get("type")
            ]
            device_nics = set(nic_types)
            filter_set = set(filter_nics)

            if nic_condition == "or":
                if not device_nics & filter_set:
                    continue
            elif nic_condition == "and":
                if not filter_set.issubset(device_nics):
                    continue

        if search_keyword_value:
            keyword = search_keyword_value.lower()
            if not matches_keyword(device, keyword):
                continue

        result.append(device)

    return result


def apply_sorting(devices: list, sort_by: str, sort_order: str) -> list:
    """
    Sort device list
    """
    if not sort_by or not sort_order:
        return devices

    sort_order = sort_order.lower()
    reverse = sort_order == 'desc'

    # Define sortable fields and corresponding extraction functions
    sort_functions = {
        'hostname': lambda x: x.get('bmc', {}).get('hostname', '').lower(),
        'ip': lambda x: x.get('device', {}).get('ip', ''),
        'user': lambda x: x.get('user', '').lower(),
        'time': lambda x: x.get('time', 0),
    }

    if sort_by not in sort_functions:
        LOG.warning(f"Unknown sort field: {sort_by}")
        return devices

    extract_func = sort_functions[sort_by]

    try:
        # Special handling for IP address sorting
        if sort_by == 'ip':
            def ip_key_func(item):
                ip = extract_func(item)
                if not ip:
                    return (0, 0, 0, 0)  # Empty IP at the front

                # Convert IP address to comparable numeric tuple
                parts = ip.split('.')
                if len(parts) != 4:
                    return (0, 0, 0, 0)

                try:
                    return tuple(int(part) for part in parts)
                except ValueError:
                    return (0, 0, 0, 0)

            sorted_devices = sorted(devices, key=ip_key_func, reverse=reverse)
        else:
            # Other fields sorted directly
            sorted_devices = sorted(devices, key=extract_func, reverse=reverse)

        return sorted_devices
    except Exception as e:
        LOG.error(f"Sorting failed: {e}")
        return devices