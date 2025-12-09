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
from brain.utils.ssh_client import ssh_execute, ssh_execute_async
from brain.api.v2.schemas import common_schemas

LOG = logging.getLogger(__name__)
BMC_USER = "ipmiadmin"
BMC_PASS = "ymxl@2022"
COMMON_USER = "tester"
COMMON_USER_PASSWORD = "Test.999"
COMMON_SERVER = "10.0.3.248"
TASK_POOL_COLLECTION = "tasks"
db = SQLiteDocumentDB()


async def ensure_packages_installed(host: str, user: str, pwd: str, packages: list):
    """
    Ensure packages (interpreted as commands) exist on remote host.
    If not, install corresponding packages (assumed same as names).
    Supports Debian / RHEL / Fedora / SUSE.
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

        elif echo "$OS" | grep -qi "rhel"; then
            curl -s -o /etc/yum.repos.d/centos7.6.repo http://mirrors.yunsilicon.com/yum.repos.d/centos7.9.repo || true
            curl -s -o /etc/yum.repos.d/epel.repo http://mirrors.yunsilicon.com/yum.repos.d/epel.repo || true
            yum clean all || true
            yum makecache || true

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

        elif echo "$OS" | grep -qi "rhel"; then
            yum install -y ${{MISSING[@]}}

        elif echo "$OS" | grep -qi "fedora"; then
            dnf install -y ${{MISSING[@]}}

        elif echo "$OS" | grep -qi "suse"; then
            zypper install -y ${{MISSING[@]}}

        else
            echo "Unsupported distro: $OS"
            exit 1
        fi
    }}

    ensure_repo
    ensure_packages
    """ # noqa

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
        host_ip, "lsblk -rno NAME,PKNAME,PARTUUID", user, pwd).splitlines()

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


async def update_automatic_async(ip, user, password):
    server_sn = await ssh_execute_async(ip, "cat /sys/class/dmi/id/product_serial", user, password)
    server_vendor = await ssh_execute_async(ip, "cat /sys/class/dmi/id/sys_vendor", user, password)
    server_product = await ssh_execute_async(
        ip, "cat /sys/class/dmi/id/product_name", user, password)

    cpu_cmd = (
        "lscpu | awk -F\":\" "
        "'/Architecture:|Vendor ID:|Model name:/ "
        "{gsub(/^[ \\t]+/, \"\", $2); print $2}'"
    )
    cpu_infos = (await ssh_execute_async(ip, cpu_cmd, user, password)).strip().split("\n")

    # PCI VPD
    pci_cmd = ("lspci -d 1f67: -vvv | awk '/Ethernet controller/ {print} "
               "/Vital Product Data/ {print; for(i=0;i<5;i++){getline; print}}'")
    pci_res = await ssh_execute_async(ip, pci_cmd, user, password)
    nics = parse_nics_info(pci_res)

    try:
        mac_res = await ssh_execute_async(ip, "yuncli mac -r", user, password)
    except Exception as e:
        LOG.warning(f"failed to retrieve MAC information, error: {e}")
        mac_res = ""

    macs = parse_bdf_mac(mac_res)

    # Remote iface map
    map_cmd = ("for i in /sys/class/net/*/address; do "
               "echo \"$(basename $(dirname $i)) $(cat $i)\"; "
               "done")
    out = await ssh_execute_async(ip, map_cmd, user, password)

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
    route_cmd = (f"ip route get {COMMON_SERVER} | head -1 | "
                 "awk '{for(i=1;i<=NF;i++) if($i==\"dev\") print $(i+1)}'")
    iface_name = await ssh_execute_async(ip, route_cmd, user, password)

    iface_mac = (await ssh_execute_async(
        ip, f"cat /sys/class/net/{iface_name}/address", user, password)).strip()
    gateway = (await ssh_execute_async(
        ip, "ip route | awk '/default/ {print $3}'", user, password)).strip()

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

            update_task(task_id, stage="reboot", detail="The server is undergoing a cold restart")
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
