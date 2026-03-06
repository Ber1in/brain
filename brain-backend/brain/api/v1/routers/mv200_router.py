# Copyright (C) 2021 - 2025, Shanghai Yunsilicon Technology Co., Ltd.
# All rights reserved.

import asyncio
import copy
import random
import re
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
import logging
import uuid
import urllib3
from urllib.parse import quote
from brain.api.v2.schemas import common_schemas

from brain.json_db import SQLiteDocumentDB
from brain.auth import authenticate_user
from brain.api.v1.schemas import mv200_schemas
from brain.clients.dpuagent import api as dpuagentApi
from brain.clients.ceph import api as ceph_api
from brain.utils.get_client import get_cephclient, get_dpuagentclient
from brain.utils.ssh_client import ssh_execute_async
from brain.utils import common_utils
from brain import exceptions

router = APIRouter(dependencies=[Depends(authenticate_user)])
LOG = logging.getLogger(__name__)
db = SQLiteDocumentDB()

# Collection name
MV_SERVER_COLLECTION = "mv_servers"
IMAGE_COLLECTION = "images"
SERVER_COLLECTION = "servers"

MV200_OS_USER = "root"
MV200_OS_PASSWORD = "yunsilicon"
IMAGE_POOL = "images"
SNAP_NAME = "brain_snap"


async def _create_system_disk(
        mv200_id, data: mv200_schemas.CloudDiskCreateRequest, creator: str, rebuild=False):
    disk_data = data.system_disk
    LOG.info(f"Starting system disk creation process for image {disk_data.image_id} "
             f"on MV200 server {mv200_id}, creator: {creator}")

    # Check if image exists
    try:
        image = db.find_one(IMAGE_COLLECTION, {"id": disk_data.image_id})
    except Exception:
        LOG.warning(f"Image '{disk_data.image_id}' not found when creating system disk")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image '{disk_data.image_id}' not found"
        )

    # Check if MV200 server exists
    mv_server = db.find_one(MV_SERVER_COLLECTION, {"id": mv200_id})
    if not mv_server:
        LOG.warning(f"MV200 server '{mv200_id}' not found when creating system disk")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MV200 server '{mv200_id}' not found"
        )

    soc_ip = mv_server.get("ip_address")
    target_server = None

    servers = db.find(SERVER_COLLECTION)
    for server in servers:
        for nic in server.get("nics", []):
            if nic.get("sn") == mv_server["nic_sn"]:
                target_server = server
                break
        if target_server:
            break

    if not target_server:
        LOG.warning(
            f"Bare Metal server not found for MV200 {soc_ip}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bare Metal server not found for MV200 {soc_ip}"
        )

    # Generate unique ID and RBD path
    host_ip = target_server["device"]["ip"]
    gateway = target_server["device"]["gateway"]
    mac = target_server["device"]["mac"]
    disk_id = data.system_disk.disk_id or str(uuid.uuid4())
    rbd_path = f"{data.system_disk.pool}/{disk_id}"

    for mon_host in data.system_disk.mon_hosts:
        try:

            LOG.info(
                f"Starting RBD clone process for disk {disk_id} from {image['ceph_location']}")
            cephclient = get_cephclient(mon_host)
            ceph_api.RbdSnapshotApi(
                cephclient).api_block_image_image_spec_snap_snapshot_name_clone_post(
                image_spec=quote(image["ceph_location"], safe=""),
                snapshot_name=SNAP_NAME,
                api_block_image_image_spec_snap_snapshot_name_clone_post_request={
                    "child_pool_name": data.system_disk.pool,
                    "child_image_name": disk_id
                }
            )
            LOG.info(f"Successfully cloned RBD image for disk {disk_id}")

            rbd_api = ceph_api.RbdApi(cephclient)
            if disk_data.flatten:
                LOG.info(f"Flattening RBD image for disk {disk_id}")
                rbd_api.api_block_image_image_spec_flatten_post(
                    image_spec=quote(rbd_path, safe=""))
                LOG.info(f"Successfully flattened RBD image for disk {disk_id}")

            LOG.info(f"Resizing RBD image for disk {disk_id} to {disk_data.size_gb}GB")
            rbd_api.api_block_image_image_spec_put(
                image_spec=quote(rbd_path, safe=""),
                api_block_image_image_spec_put_request={
                    "size": disk_data.size_gb * 1024 * 1024 * 1024}
            )
            LOG.info(f"Successfully resized RBD image for disk {disk_id}")
            break

        except Exception as e:
            LOG.warning(f"Failed to clone system disk {disk_id} on mon_host {mon_host}, error: {e}")

    else:
        msg = f"Failed to clone system disk {disk_id}"
        LOG.error(msg)
        raise exceptions.CloneSystemdiskException(msg)

    # Create virtual block device
    LOG.info(f"Creating virtual block device for disk {disk_id} on SOC {soc_ip}")
    dpuagentclient = get_dpuagentclient(soc_ip)
    blk_api = dpuagentApi.VblkApi(dpuagentclient)
    try:
        res = blk_api.create_vblk_dpu_agent_v1_vblk_add_post(
            dpuagent_api_v1_schemas_vblk_schemas_create_request={
                "rbd_path": rbd_path,
                "gw_pwd": "yunsilicon",
                "gws": data.system_disk.mon_hosts,
                "vq_count": data.system_disk.vq_count,
                "vq_size": data.system_disk.vq_size,
                "bootable": True,
                "gw_user": "admin"
            })
        LOG.info(f"Virtual block device creation response for disk {disk_id}:"
                 f" code={res.code}, message={res.message}")
    except Exception as e:
        LOG.error(f"Failed to create virtblk for disk {disk_id} in {soc_ip}, error: {e}")
        raise exceptions.VblkCreateException(str(e))

    if res.code != 0:
        LOG.error(
            f"Failed to create virtblk for disk {disk_id} in {soc_ip}, message: {res.message}")
        raise exceptions.VblkCreateException(res.message)

    LOG.info(f"Successfully created virtual block device for disk {disk_id} with UUID: {res.uuid}")

    cloudinit_status = 0
    # Set system user and cloudinit configuration
    if not rebuild:
        LOG.info(f"Configuring cloudinit for disk {disk_id}")
        system_user = data.system_user
        user_data = {"users": [{"name": system_user.name,
                                "password": system_user.password}]}
        if target_server["bmc"].get("hostname"):
            user_data["hostname"] = re.sub(
                r'[^A-Za-z0-9-]', '', target_server["bmc"].get("hostname")) or "default-host"

        network_config = {
            "version": 1,
            "ethernets": 
            [
                {
                    "name": "eth0",
                    "mac": mac,
                    "dhcp4": False,
                    "dhcp6": False,
                    "addresses": [
                        f"{host_ip}/24"
                    ],
                    "gateway4": gateway,
                    # "nameservers": [
                    #     "10.0.0.50",
                    #     "10.0.0.51"
                    # ],
                }
            ]
        }
        try:
            cloudinit_api = dpuagentApi.CloudinitApi(dpuagentclient)
            res = cloudinit_api.create_cloudinit_dpu_agent_v1_cloudinit_create_post(
                {"user_data": user_data, "network_config": network_config})
            if res.code != 0:
                LOG.warning(f"Failed to create cloudinit datasource for SOC {soc_ip} and"
                            f" disk {disk_id}, message: {res.message}")
                cloudinit_status = 1
            else:
                LOG.info(f"Successfully configured cloudinit for disk {disk_id}")
        except Exception as e:
            LOG.error("Failed to create cloudinit datasource for SOC"
                      f" {soc_ip} and disk {disk_id}, error: {e}")
            cloudinit_status = 1
    else:
        LOG.info(f"Skipping cloudinit configuration for disk {disk_id}")

    # Save checkpoint
    LOG.info(f"Saving checkpoint for disk {disk_id}")
    try:
        recoverapi = dpuagentApi.RecoveryApi(dpuagentclient)
        res = recoverapi.save_checkpoint_dpu_agent_v1_checkpoint_save_post()
        if res.code != 0:
            LOG.error(f"Failed to save checkpoint for disk {disk_id}: {res.message}")
            raise exceptions.CheckPointSaveException(res.message)
        LOG.info(f"Successfully saved checkpoint for disk {disk_id}")
    except Exception as e:
        LOG.error(f"Failed to save checkpoint after creating block {disk_id}: {e}")
        raise

    efi_status = 0
    if target_server["device"].get("username") and target_server["device"].get("password"):
        try:
            efi_uuid = await create_efi_boot_entry(
                host_ip, target_server["device"].get("username"),
                target_server["device"].get("password"), data.system_disk.size_gb,
                disk_id, image["name"])
            if not efi_uuid:
                efi_status = 1
            else:
                LOG.info(
                    f"EFI create succeeded for server {target_server['id']}, entry: {efi_uuid}")
        except Exception as e:
            LOG.warning(
                f"EFI create failed for server {target_server['id']}: {e}. "
                "Frontend will be notified with special code."
            )
            efi_status = 1
    else:
        LOG.warning(
            f"Skipping EFI creating for server {target_server['id']} due to missing credentials"
        )
        efi_status = 1

    LOG.info(f"Successfully created system disk {disk_id}")

    return {"efi_status": efi_status, "cloudinit_status": cloudinit_status}


async def create_efi_boot_entry(host_ip: str, username: str, password: str, 
                                expected_size_gb: int, disk_id: str, image_name: str) -> str | None:
    """
    Create an EFI boot entry for a cloud system disk. Returns PARTUUID if successful.

    Args:
        host_ip: IP address of the physical host
        username: SSH username
        password: SSH password
        expected_size_gb: Expected disk size in GB
        disk_id: Disk ID used to generate the boot entry name

    Returns:
        str or None: PARTUUID if EFI boot entry is created or exists, None otherwise
    """
    LOG.info(f"Creating EFI boot entry for disk {disk_id} on host {host_ip}")

    try:
        # Wait for the device to be recognized
        await ssh_execute_async(host_ip, "sleep 3", username, password)

        # Rescan PCIe devices
        await ssh_execute_async(host_ip, "echo 1 > /sys/bus/pci/rescan", username, password)
        await ssh_execute_async(host_ip, "sleep 2", username, password)

        # Get virtio disk information
        disk_info_cmd = (
            "for dev in /sys/block/vd*; do "
            "if [ -d \"$dev\" ]; then "
            "dev_name=$(basename \"$dev\"); "
            "size=$(cat \"$dev/size\" 2>/dev/null || echo 0); "
            "size_gb=$((size * 512 / 1024 / 1024 / 1024)); "
            "add_time=$(stat -c %Y \"$dev\" 2>/dev/null || echo 0); "
            "echo \"$dev_name $size_gb $add_time\"; "
            "fi; done"
        )
        disk_info_output = await ssh_execute_async(host_ip, disk_info_cmd, username, password)

        # Parse disks and find candidates matching expected size
        disks = []
        for line in disk_info_output.splitlines():
            parts = line.split()
            if len(parts) >= 3:
                disk_name, size_gb, add_time = parts[0], int(parts[1]), int(parts[2])
                if abs(size_gb - expected_size_gb) <= 1:
                    disks.append({'name': disk_name, 'add_time': add_time})

        if not disks:
            LOG.warning(f"No disks found matching expected size {expected_size_gb}GB")
            return None

        # Select the most recently added disk
        target_device = sorted(disks, key=lambda x: x['add_time'])[-1]['name']

        # Get the first partition of the target disk
        partitions_output = await ssh_execute_async(
            host_ip,
            f"lsblk -nlo NAME /dev/{target_device} | grep -E '{target_device}[0-9]+'",
            username, password
        )
        if not partitions_output:
            LOG.warning(f"No partitions found on /dev/{target_device}")
            return None
        target_partition = partitions_output.splitlines()[0].strip()

        # Get PARTUUID of the partition
        partuuid_output = await ssh_execute_async(
            host_ip, f"lsblk -no PARTUUID /dev/{target_partition}", username, password
        )
        if not partuuid_output or not partuuid_output.strip():
            LOG.warning(f"No PARTUUID found for /dev/{target_partition}")
            return None
        partuuid = partuuid_output.strip()

        # Check if a boot entry already exists
        existing_entries = await ssh_execute_async(host_ip, "efibootmgr -v", username, password)
        for line in existing_entries.splitlines():
            if partuuid in line:
                LOG.info(f"Boot entry already exists for PARTUUID {partuuid}")
                return partuuid

        partition_number = target_partition[len(target_device):]  

        try:
            # Create temporary mount point
            mount_point_cmd = "mktemp -d"
            mount_point = (await ssh_execute_async(
                host_ip, mount_point_cmd, username, password)).strip()

            # Mount the EFI partition of the target device
            mount_cmd = f"mount /dev/{target_partition} {mount_point}"
            await ssh_execute_async(host_ip, mount_cmd, username, password)

            try:
                # Preferentially search for shimx64.efi (Secure Boot compatible)
                efi_files = await ssh_execute_async(
                    host_ip,
                    f"find {mount_point} -name shimx64.efi -type f", username, password)
                shim_efis = efi_files.strip().split('\n')
                shim_efis = [efi for efi in shim_efis if efi]

                if shim_efis:
                    # Prefer using shimx64.efi
                    selected_efi = shim_efis[0]
                    LOG.info("Using shimx64.efi for Secure Boot compatibility")
                else:
                    # Fall back to grubx64.efi if shim is not found
                    efi_files = await ssh_execute_async(
                        host_ip,
                        f"find {mount_point} -name grubx64.efi -type f", username, password)
                    grub_efis = efi_files.strip().split('\n')
                    grub_efis = [efi for efi in grub_efis if efi]

                    if grub_efis:
                        selected_efi = grub_efis[0]
                        LOG.info("Using grubx64.efi (Secure Boot may be disabled)")
                    else:
                        LOG.error(f"No suitable EFI files found on /dev/{target_partition}")
                        return None

                # Convert absolute path to relative path within the EFI partition
                relative_efi_path = selected_efi.replace(mount_point, "").replace("/", "\\")
                LOG.info(f"Selected EFI file: {selected_efi}, UEFI path: {relative_efi_path}")

                # Determine boot entry name based on EFI path
                if "centos" in relative_efi_path.lower():
                    boot_entry_name = "CentOS Boot Manager"
                elif "ubuntu" in relative_efi_path.lower():
                    boot_entry_name = "Ubuntu"
                elif "redhat" in relative_efi_path.lower():
                    boot_entry_name = "Red Hat Enterprise Linux"
                elif "rocky" in relative_efi_path.lower():
                    boot_entry_name = "Rocky Linux"
                elif "alma" in relative_efi_path.lower():
                    boot_entry_name = "AlmaLinux"
                elif "debian" in relative_efi_path.lower():
                    boot_entry_name = "Debian"
                else:
                    safe_image_name = re.sub(r'[^A-Za-z0-9-]', '', image_name)
                    boot_entry_name = f"{safe_image_name}"

                # Create EFI boot entry
                efi_cmd = (
                    f"efibootmgr -c -d /dev/{target_device} -p {partition_number} "
                    f"-L \"{boot_entry_name}\" -l \"{relative_efi_path}\""
                )
                result = await ssh_execute_async(host_ip, efi_cmd, username, password)
                LOG.info(f"EFI boot entry creation result: {result}")

            finally:
                # Cleanup: unmount partition and remove temporary directory
                await ssh_execute_async(host_ip, f"umount {mount_point}", username, password)
                await ssh_execute_async(host_ip, f"rmdir {mount_point}", username, password)

        except Exception as e:
            LOG.error(f"An exception occurred while creating EFI boot entry: {e}")
            return None

        LOG.info("Created EFI boot entry successfully")
        return partuuid

    except Exception as e:
        LOG.error(f"Failed to create EFI boot entry for disk {disk_id}: {e}")
        return None


@router.post("/mv-servers", response_model=mv200_schemas.MVServer,
             status_code=status.HTTP_201_CREATED)
async def create_mv_server(server_data: mv200_schemas.MVServerCreate):
    """
    Create a new MV server
    """
    LOG.info(f"Received request to create MV server: {server_data.name}")

    # Check if name already exists
    existing_server = db.find(MV_SERVER_COLLECTION, {"name": server_data.name})
    if existing_server:
        LOG.warning(f"MV server name {server_data.name} already exists")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Server with this name already exists"
        )

    # Check if IP address already exists
    existing_ip = db.find(MV_SERVER_COLLECTION, {"ip_address": server_data.ip_address})
    if existing_ip:
        LOG.warning(f"MV server IP {server_data.ip_address} already exists")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Server with this IP address already exists"
        )

    device, nics = await common_utils.update_automatic_async(
        str(server_data.ip_address), MV200_OS_USER, MV200_OS_PASSWORD
    )

    # The mv200 does not currently record the manufacturer, serial number, or product,
    # as these are all currently 'Default string'.
    [device.pop(k, None) for k in ["sn", "vendor", "product", "arch", "cpu_vendor", "cpu_mode"]]

    # Generate unique ID and create server document
    server_id = str(uuid.uuid4())
    server_dict = {
        "id": server_id,
        **server_data.dict(),
        "nic_sn": nics[0]["sn"],
        "task_id": ""
    }
    server_dict.update(device)

    LOG.info(f"Creating MV server {server_id} with IP {server_data.ip_address}")

    # Get clouddisk enable status from SOC
    LOG.info(f"Getting clouddisk enable status from SOC {server_data.ip_address}")
    server_dict["clouddisk_enable"] = False

    dpuagentclient = get_dpuagentclient(server_data.ip_address)
    try:
        setapi = dpuagentApi.SettingsApi(dpuagentclient)
        res = setapi.get_clouddisk_enable_setting_dpu_agent_v1_settings_clouddisk_enable_get(
            _request_timeout=2)
        if res.code != 0:
            LOG.error(f"Failed to get clouddisk enable status for SOC "
                      f"{server_data.ip_address}, message: {res.message}")
        else:
            server_dict["clouddisk_enable"] = res.clouddisk_enable
            LOG.info(f"Clouddisk enable status for SOC {server_data.ip_address}: "
                     f"{res.clouddisk_enable}")
    except Exception as e:
        LOG.error(f"Failed to get clouddisk_enable for {server_data.ip_address}, error: {e}")

    # Get clouddisk enable status from SOC
    LOG.info(f"Getting recovery mode from SOC {server_data.ip_address}")
    server_dict["recovery_mode"] = ""

    try:
        # setapi = dpuagentApi.RecoveryApi(dpuagentclient)
        # res = setapi.query_recovery_mode_dpu_agent_v1_recoverymode_query_get(
        #     _request_timeout=2)
        # if res.code != 0:
        #     LOG.error(f"Failed to get recovery mode from SOC "
        #               f"{server_data.ip_address}, message: {res.message}")
        # else:
        #     server_dict["recovery_mode"] = res.mode
        #     LOG.info(f"Recovery mode from SOC {server_data.ip_address}: "
        #              f"{res.mode}")
        res = await ssh_execute_async(server_data.ip_address, 
                                      "cat /opt/dpuagent/mode", "root", "yunsilicon")
        server_dict["recovery_mode"] = res.strip()
    except Exception as e:
        LOG.error(f"Failed to get recovery mode for {server_data.ip_address}, error: {e}")

    # Insert new server
    db.insert(MV_SERVER_COLLECTION, server_dict)
    LOG.info(f"Successfully created MV server {server_id}")

    # Return the created server information
    return server_dict


@router.get("/mv-servers", response_model=List[mv200_schemas.MVServer])
async def get_all_mv_servers():
    """
    Get all MV servers list
    """
    LOG.info("Received request to get all MV servers")
    servers = db.find(MV_SERVER_COLLECTION, {})

    LOG.info(f"Retrieved {len(servers)} MV200 servers from database")
    return servers


@router.get("/mv-servers/{server_id}", response_model=mv200_schemas.MVServer)
async def get_mv_server(server_id: str):
    """
    Get specific MV server by ID
    """
    LOG.info(f"Received request to get MV server {server_id}")
    try:
        server = db.find_one(MV_SERVER_COLLECTION, {"id": server_id})
    except Exception:
        LOG.warning(f"MV server {server_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MV server not found"
        )
    data = {}
    try:
        cmd = "yuncli fw --config read /tmp/brain_mv200.cfg >/dev/null 2>&1 && grep -E '^(sub_product_id|switch_emu_enable|vm_emu_enable)=' /tmp/brain_mv200.cfg"
        res = await ssh_execute_async(server["ip_address"], cmd, MV200_OS_USER, MV200_OS_PASSWORD, False)

        for line in res.splitlines():
            k, v = line.split("=")
            data[k] = v

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Failed to connect to DPU agent at {server['ip_address']}"
        )

    try:
        dpuagentclient = get_dpuagentclient(server["ip_address"])
        setting_api = dpuagentApi.SettingsApi(dpuagentclient)
        res = setting_api.get_clouddisk_enable_setting_dpu_agent_v1_settings_clouddisk_enable_get(
            _request_timeout=2)
        if res.code != 0:
            LOG.error(f"Failed to get clouddisk enable status for SOC "
                      f"{server['ip_address']}, message: {res.message}")
        else:
            server["clouddisk_enable"] = res.clouddisk_enable
            LOG.info(f"Clouddisk enable status for SOC {server['ip_address']}: "
                     f"{res.clouddisk_enable}")

        # setting_api = dpuagentApi.RecoveryApi(get_dpuagentclient(server["ip_address"]))
        # res = setting_api.query_recovery_mode_dpu_agent_v1_recoverymode_query_get(
        #     _request_timeout=2)
        # if res.code != 0:
        #     LOG.error(f"Failed to get recovery mode for SOC "
        #               f"{server['ip_address']}, message: {res.message}")
        # else:
        #     server["recovery_mode"] = res.mode.value
        #     LOG.info(f"Recovery mode for SOC {server['ip_address']}: "
        #              f"{res.mode}")
        res = await ssh_execute_async(server['ip_address'],
                                      "cat /opt/dpuagent/mode", "root", "yunsilicon")
        server["recovery_mode"] = res.strip()
        server_original = copy.deepcopy(server)
        versionapi = dpuagentApi.VersionApi(dpuagentclient)
        res = versionapi.get_version_dpu_agent_v1_version_get()
        if res.code != 0:
            LOG.error("Failed to retrieve version information for each service on mv200.")
        else:
            versions = {
                "driver": res.driver,
                "firmware": res.firmware,
                "dpuagent": res.dpuagent
            }
            server["versions"] = versions
            
        db.update(MV_SERVER_COLLECTION, {"id": server_id}, server_original)

    except (urllib3.exceptions.ConnectTimeoutError, urllib3.exceptions.MaxRetryError):
        # raise HTTPException(
        #     status_code=status.HTTP_504_GATEWAY_TIMEOUT,
        #     detail=f"Failed to connect to DPU agent at {server['ip_address']}"
        # )
    # except dpuagentExp.NotFoundException:
        LOG.warning(f"The server {server['ip_address']} dpuagent service is not enabled")

    server.update(data)
    LOG.info(f"Successfully retrieved MV server {server_id}")
    return server


@router.put("/mv-servers/{server_id}", response_model=mv200_schemas.MVServer)
async def update_mv_server(server_id: str, update_data: mv200_schemas.MVServerUpdate):
    """
    Update MV server information by ID
    """
    LOG.info(f"Received request to update MV server {server_id}")

    # Check if server exists
    existing_server = db.find_one(MV_SERVER_COLLECTION, {"id": server_id})
    if not existing_server:
        LOG.warning(f"MV server {server_id} not found for update")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MV server not found"
        )

    # If updating name, check if name conflicts with other servers
    if update_data.name and update_data.name != existing_server.get("name"):
        same_name_servers = db.find(MV_SERVER_COLLECTION, {"name": update_data.name})
        if same_name_servers:
            LOG.warning(f"MV server name {update_data.name} conflicts with existing server")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Another server with this name already exists"
            )

    # If updating IP address, check if IP conflicts with other servers
    if update_data.ip_address and update_data.ip_address != existing_server.get("ip_address"):
        same_ip_servers = db.find(MV_SERVER_COLLECTION, {"ip_address": update_data.ip_address})
        if same_ip_servers:
            LOG.warning(f"MV server IP {update_data.ip_address} conflicts with existing server")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Another server with this IP address already exists"
            )

    # Update server information (excluding ID field)
    update_dict = {k: v for k, v in update_data.dict().items() if v is not None}

    if update_dict.pop("auto"):
        LOG.info(f"Automatic updating mv200: {server_id}")

        device, nics = await common_utils.update_automatic_async(
            update_data.ip_address,
            MV200_OS_USER,
            MV200_OS_PASSWORD
        )

        # The mv200 does not currently record the manufacturer, serial number, or product,
        # as these are all currently 'Default string'.
        [device.pop(k, None) for k in ["sn", "vendor", "product", "arch", "cpu_vendor", "cpu_mode"]]

        update_dict.update(device)
        update_dict["nic_sn"] = nics[0]["sn"]

    if update_dict:
        LOG.info(f"Updating MV server {server_id} with fields: {list(update_dict.keys())}")

        soc_ip = existing_server["ip_address"]
        # Handle clouddisk enable status update
        if update_data.clouddisk_enable != existing_server.get("clouddisk_enable"):
            new_status = update_data.clouddisk_enable
            LOG.info(f"Updating clouddisk enable status for SOC {soc_ip} to {new_status}")
            setting_api = dpuagentApi.SettingsApi(get_dpuagentclient(soc_ip))
            res = setting_api.enable_pxe_dpu_agent_v1_settings_clouddisk_enable_put(
                {"clouddisk_enable": update_data.clouddisk_enable})
            if res.code != 0:
                LOG.error(f"Failed to update clouddisk enable status for SOC "
                          f"{soc_ip}, message: {res.message}")
                update_dict["clouddisk_enable"] = existing_server["clouddisk_enable"]
                LOG.warning(f"Reverted clouddisk enable status to original value: "
                            f"{existing_server['clouddisk_enable']}")
            else:
                LOG.info(f"Successfully updated clouddisk enable status for SOC {soc_ip}")

        if update_data.recovery_mode != existing_server.get("recovery_mode"):
            new_mode = update_data.recovery_mode
            LOG.info(f"Updating recovery mode for SOC {soc_ip} to {new_mode}")

            try:
                recovery_api = dpuagentApi.RecoveryApi(get_dpuagentclient(soc_ip))
                res = recovery_api.update_recovery_mode_dpu_agent_v1_recoverymode_update_post(
                    {"mode": new_mode}
                )

                if res.code != 0:
                    LOG.error(
                        f"Failed to update recovery mode for SOC {soc_ip}, message: {res.message}")
                    update_dict["recovery_mode"] = existing_server["recovery_mode"]
                    LOG.warning(f"Reverted recovery mode to original value: "
                                f"{existing_server['recovery_mode']}")
                else:
                    LOG.info(f"Successfully updated recovery mode for SOC {soc_ip}")

            except Exception as e:
                LOG.error(f"Exception while updating recovery mode for SOC {soc_ip}: {e}")
                update_dict["recovery_mode"] = existing_server["recovery_mode"]
                LOG.warning(f"Reverted recovery mode to original value: "
                            f"{existing_server['recovery_mode']}")

        updated_count = db.update(MV_SERVER_COLLECTION, {"id": server_id}, update_dict)
        if updated_count == 0:
            LOG.error(f"Failed to update MV server {server_id} in database")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="MV server not found"
            )
        LOG.info(f"Successfully updated MV server {server_id} in database")
    else:
        LOG.info(f"No fields to update for MV server {server_id}")

    # Return updated server information
    updated_server = db.find_one(MV_SERVER_COLLECTION, {"id": server_id})
    LOG.info(f"Successfully completed update for MV server {server_id}")
    return updated_server


@router.delete("/mv-servers/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mv_server(server_id: str):
    """
    Delete MV server by ID
    """
    LOG.info(f"Received request to delete MV server {server_id}")

    # Check if server exists
    existing_servers = db.find(MV_SERVER_COLLECTION, {"id": server_id})
    if not existing_servers:
        LOG.warning(f"MV server {server_id} not found for deletion")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MV server not found"
        )

    server_name = existing_servers[0].get("name", "unknown")
    server_ip = existing_servers[0].get("ip_address", "unknown")
    LOG.info(f"Deleting MV server {server_id} ({server_name}) with IP {server_ip}")

    # Delete server
    deleted_count = db.delete(MV_SERVER_COLLECTION, {"id": server_id})
    if deleted_count == 0:
        LOG.error(f"Failed to delete MV server {server_id} from database")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MV server not found"
        )

    LOG.info(f"Successfully deleted MV server {server_id}")


@router.post("/mv-servers/{server_id}/update_mcr", status_code=202)
async def update_mcr(server_id: str, data: common_schemas.MCRRequest):
    LOG.info("Received MCR update request for server_id="
             f"{server_id} with options={data.update_options}")

    # Fetch server information
    try:
        server = db.find_one(MV_SERVER_COLLECTION, {"id": server_id})
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
    db.update(MV_SERVER_COLLECTION, {"id": server_id}, server)

    host_ipmi = ""
    # Run background task
    asyncio.create_task(
        common_utils.run_mcr_update_task(
            task_id, server["ip_address"],
            MV200_OS_USER, MV200_OS_PASSWORD, host_ipmi, data, aidpu=True)
    )
    LOG.info(f"Background task {task_id} started for server {server_id}")

    return {"message": "MCR update task accepted", "task_id": task_id}


@router.get("/mv-servers/{server_id}/xsc", response_model=List[mv200_schemas.XscnetInfoResponse])
async def get_interface(server_id: str, uuid: Optional[int] = Query(None, ge=1, le=100)):
    """Get network interface(s) info"""
    try:
        mv200 = db.find_one(MV_SERVER_COLLECTION, {"id": server_id})
    except Exception:
        LOG.warning(f"mv200 {server_id} not found")
        raise HTTPException(status_code=404, detail="mv200 not found")

    mv200_ip = mv200["ip_address"]
    LOG.info(f"Fetching interface for {mv200_ip}")

    try:
        dpuagentclient = get_dpuagentclient(mv200_ip)

        if uuid is None:
            res = dpuagentApi.XscnetApi(
                dpuagentclient).list_xsc_controllers_dpu_agent_v1_xscnet_list_get()
        else:
            res = dpuagentApi.XscnetApi(
                dpuagentclient).list_xsc_controllers_dpu_agent_v1_xscnet_list_get(uuid)

        if res.code != 0:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=f"Failed to list xscnet at {mv200_ip}"
            )

        xscs = res.to_dict().get("xscnets") or []
    except Exception as e:
        LOG.warning(f"Failed to obtain the network port name, error: {e}")
        return []

    try:
        res = dpuagentApi.RdmaApi(dpuagentclient).list_nics_info_dpu_agent_v1_rdma_list_nics_get()
        nics_info = res.nics_info or []
    except Exception as e:
        LOG.warning(f"Failed to obtain the network port name, error: {e}")
        nics_info = []

    nic_index = {}
    for nic in nics_info:
        if not nic.mac or not nic.ip_addr:
            continue
        # if nic.ip_addr == "0.0.0.0":
        #     continue

        mac = nic.mac.lower().replace("-", ":")
        ip = nic.ip_addr.strip()

        nic_index[(mac, ip)] = nic.ifname

    for xsc in xscs:
        if not xsc.get("mac"):
            continue

        xsc_mac = xsc["mac"].lower()
        xsc_ip = xsc.get("ip", "0.0.0.0").split("/", 1)[0]

        ifname = nic_index.get((xsc_mac, xsc_ip))
        if ifname:
            xsc["ifname"] = ifname

    LOG.info(f"Interface for {mv200_ip} fetched successfully")
    return xscs


@router.post("/mv-servers/{server_id}/xsc", response_model=mv200_schemas.XscnetInfoResponse)
async def create_interface(server_id: str, data: mv200_schemas.InterfaceCreate):
    """Create a new network interface"""
    LOG.info(f"Creating interface on SoC {server_id}")

    try:
        server = db.find_one(MV_SERVER_COLLECTION, {"id": server_id})
    except Exception:
        LOG.warning(f"MV server {server_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="MV server not found"
        )

    iface_data = data.dict()
    if not iface_data.get("mac"):
        iface_data["mac"] = "02:00:%02x:%02x:%02x:%02x" % (
            random.randint(0x00, 0x7f),
            random.randint(0x00, 0xff),
            random.randint(0x00, 0xff),
            random.randint(0x00, 0xff),
        )
        LOG.info(f"Generated MAC {iface_data['mac']} for interface")

    dpuagentclient = get_dpuagentclient(server["ip_address"])
    xscapi = dpuagentApi.XscnetApi(dpuagentclient)
    try:
        params = {
            "pxe": data.pxe,
            "vq_count": data.vq_count,
            "vq_size": data.vq_size,
            "mac": iface_data["mac"],
            "mtu": data.mtu,
        }
        if data.uuid is not None:
            params["uuid"] = data.uuid
        res = xscapi.create_xscnet_dpu_agent_v1_xscnet_add_post(params)
        if res.code != 0:
            LOG.error(
                f"Failed to create XSC network for interface "
                f"on SoC {server['ip_address']}: {res.message}"
            )
            raise HTTPException(status_code=500, detail=res.message)
        iface_data["xsc_id"] = res.uuid
        LOG.info(
            f"XSC network created for interface {res.uuid}, uuid={res.uuid}"
        )
    except Exception as e:
        LOG.error(f"Exception creating XSC network: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    # Save checkpoint
    LOG.info(f"Saving checkpoint for xsc {iface_data.get('xsc_id')}")
    try:
        recoverapi = dpuagentApi.RecoveryApi(dpuagentclient)
        res = recoverapi.save_checkpoint_dpu_agent_v1_checkpoint_save_post()
        if res.code != 0:
            LOG.error(
                f"Failed to save checkpoint for xsc {iface_data.get('xsc_id')}: {res.message}")
            raise exceptions.CheckPointSaveException(res.message)
        LOG.info(f"Successfully saved checkpoint for xsc {iface_data.get('xsc_id')}")
    except Exception as e:
        LOG.error(
            f"Failed to save checkpoint after creating xsc {iface_data.get('xsc_id')}: {e}")
        raise

    return {"uuid": iface_data.get('xsc_id'), "mtu": data.mtu, "mac": iface_data["mac"]}


@router.post("/mv-servers/{server_id}/xsc/{uuid}/flowtables", 
             status_code=status.HTTP_204_NO_CONTENT)
async def configure_interface_flow_tables(
        server_id: str, uuid: int, data: mv200_schemas.OvsflowRequest):
    # Fetch server information
    try:
        mv200 = db.find_one(MV_SERVER_COLLECTION, {"id": server_id})
    except Exception as e:
        LOG.error(f"Failed to fetch server {server_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch server info")

    dpuagentclient = get_dpuagentclient(mv200["ip_address"])
    ovsapi = dpuagentApi.OvsflowApi(dpuagentclient)
    try:
        params = {
            "uuid": uuid,
            "vlan": data.vlan_tag,
            "ip": str(data.ip),
            "src_mac": data.mac
        }
        if data.dns:
            params["dns"] = data.dns
        if data.gateway:
            params["gw_ip"] = data.gateway
        if data.dhcp_server:
            params["dhcp_server"] = data.dhcp_server
        res = ovsapi.add_ovsflow_dpu_agent_v1_ovsflow_add_post(params)
        if res.code != 0:
            LOG.error(
                f"Failed to add OVS flow for interface {uuid} "
                f"on SoC {mv200['ip_address']}: {res.message}"
            )
            raise HTTPException(status_code=500, detail=res.message)
        LOG.info(f"OVS flow added for interface {uuid} successfully")
    except Exception as e:
        LOG.error(f"Exception adding OVS flow for {uuid}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    # Save checkpoint
    LOG.info(f"Saving checkpoint for xsc interface {uuid}")
    try:
        recoverapi = dpuagentApi.RecoveryApi(dpuagentclient)
        res = recoverapi.save_checkpoint_dpu_agent_v1_checkpoint_save_post()
        if res.code != 0:
            LOG.error(f"Failed to save checkpoint for interface {uuid}: {res.message}")
            raise exceptions.CheckPointSaveException(res.message)
        LOG.info(f"Successfully saved checkpoint for interface {uuid}")
    except Exception as e:
        LOG.error(f"Failed to save checkpoint after creating interface {uuid}: {e}")
        raise


@router.delete("/mv-servers/{server_id}/xsc/{uuid}/flowtables",
               status_code=status.HTTP_204_NO_CONTENT)
async def delete_interface_flow_tables(
        server_id: str, uuid: int):
    # Fetch server information
    try:
        mv200 = db.find_one(MV_SERVER_COLLECTION, {"id": server_id})
    except Exception as e:
        LOG.error(f"Failed to fetch server {server_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch server info")

    dpuagentclient = get_dpuagentclient(mv200["ip_address"])
    ovsapi = dpuagentApi.OvsflowApi(dpuagentclient)
    try:
        params = {
            "uuid": uuid
        }
        res = ovsapi.del_ovsflow_dpu_agent_v1_ovsflow_del_post(params)
        if res.code != 0:
            LOG.error(
                f"Failed to del OVS flow for interface {uuid} "
                f"on SoC {mv200['ip_address']}: {res.message}"
            )
            raise HTTPException(status_code=500, detail=res.message)
        LOG.info(f"OVS flow deleted for interface {uuid} successfully")
    except Exception as e:
        LOG.error(f"Exception deleting OVS flow for {uuid}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    # Save checkpoint
    LOG.info(f"Saving checkpoint for xsc interface {uuid}")
    try:
        recoverapi = dpuagentApi.RecoveryApi(dpuagentclient)
        res = recoverapi.save_checkpoint_dpu_agent_v1_checkpoint_save_post()
        if res.code != 0:
            LOG.error(f"Failed to save checkpoint for interface {uuid}: {res.message}")
            raise exceptions.CheckPointSaveException(res.message)
        LOG.info(f"Successfully saved checkpoint for interface {uuid}")
    except Exception as e:
        LOG.error(f"Failed to save checkpoint after deleting interface {uuid}: {e}")
        raise


@router.delete("/mv-servers/{server_id}/xsc/{uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_interface(server_id: str, uuid: int):
    """Delete an existing network interface"""
    try:
        server = db.find_one(MV_SERVER_COLLECTION, {"id": server_id})
    except Exception:
        LOG.warning(f"MV server {server_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="MV server not found"
        )

    LOG.info(f"Deleting interface {uuid} on SoC {server['ip_address']}")
    dpuagentclient = get_dpuagentclient(server['ip_address'])
    try:
        res = dpuagentApi.XscnetApi(dpuagentclient).delete_xscnet_dpu_agent_v1_xscnet_del_post(
            {"uuid": uuid}
        )
        if res.code != 0:
            LOG.error(
                f"Failed to delete XSC network for interface {uuid} "
                f"on SoC {server['ip_address']}: {res.message}"
            )
            raise HTTPException(status_code=500, detail=res.message)
        LOG.info(f"XSC network for interface {uuid} deleted successfully")
    except Exception as e:
        LOG.error(f"Exception deleting XSC network for {uuid}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    # Save checkpoint
    LOG.info(f"Saving checkpoint for xsc interface {uuid}")
    try:
        recoverapi = dpuagentApi.RecoveryApi(dpuagentclient)
        res = recoverapi.save_checkpoint_dpu_agent_v1_checkpoint_save_post()
        if res.code != 0:
            LOG.error(f"Failed to save checkpoint for interface {uuid}: {res.message}")
            raise exceptions.CheckPointSaveException(res.message)
        LOG.info(f"Successfully saved checkpoint for interface {uuid}")
    except Exception as e:
        LOG.error(f"Failed to save checkpoint after deleting interface {uuid}: {e}")
        raise
    LOG.info(f"Interface {uuid} deleted successfully")
    return


@router.get("/mv-servers/{server_id}/systemdisks", 
            response_model=List[mv200_schemas.ControllerInfo])
async def get_systemdisks(server_id: str, uuid: Optional[int] = Query(None, ge=1, le=100)):
    """Get cloud disk(s) info"""

    try:
        mv200 = db.find_one(MV_SERVER_COLLECTION, {"id": server_id})
    except Exception:
        LOG.warning(f"mv200 {server_id} not found")
        raise HTTPException(status_code=404, detail="mv200 not found")

    mv200_ip = mv200["ip_address"]
    LOG.info(f"Fetching cloud disk for {mv200_ip}")

    blocks = []
    try:
        dpuagentclient = get_dpuagentclient(mv200_ip)

        if uuid is None:
            res = dpuagentApi.VblkApi(
                dpuagentclient).list_vblk_controllers_dpu_agent_v1_vblk_list_get()
        else:
            res = dpuagentApi.VblkApi(
                dpuagentclient).list_vblk_controllers_dpu_agent_v1_vblk_list_get(uuid)

        if res.code != 0:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=f"Failed to list cloud-disk at {mv200_ip}"
            )
        blocks = res.dict()["vblks"]
    except Exception as e:
        LOG.warning(f"Failed to list the cloud disk, error: {e}")

    LOG.info(f"system disk for {mv200_ip} fetched successfully")
    return blocks


@router.post("/mv-servers/{server_id}/system-disks/create", status_code=status.HTTP_201_CREATED,
             response_model=mv200_schemas.SystemDiskCreateResponse)
async def create_system_disk(
    server_id: str,
    data: mv200_schemas.CloudDiskCreateRequest, 
    user=Depends(authenticate_user)
):
    """
    Create a new system disk RBD from image for specific MV200 server
    """
    LOG.info(f"Received request to create system disk for MV200 {server_id} "
             f"with image {data.system_disk.image_id}, creator: {user}")
    try:
        result = await _create_system_disk(server_id, data, user)
        LOG.info(f"Successfully completed system disk creation request "
                 f"with image {data.system_disk.image_id}")
        return result
    except Exception as e:
        LOG.error(f"Failed to complete system disk creation request: {e}")
        raise


async def _delete_system_disk(mv200_id, data: mv200_schemas.SystemDiskDeleteRequest, rebuild=False):
    mv200 = db.find_one(MV_SERVER_COLLECTION, {"id": mv200_id})
    soc_ip: str = mv200["ip_address"]
    pool, disk_id = data.rbd_path.split("/")
    is_last_disk: bool = data.last_disk
    LOG.info(f"Starting deletion process for system disk {disk_id}")

    # Check if disk exists

    LOG.info(f"Found disk {disk_id} with SOC IP: {soc_ip}, mon_hosts: {data.mon_hosts}")

    dpuagentclient = get_dpuagentclient(soc_ip)

    # Check if this is the last disk on the SOC
    LOG.info(f"Disk {disk_id} is {'last' if is_last_disk else 'not last'} disk on SOC {soc_ip}")

    efi_status = 0
    cloudinit_status = 0
    if is_last_disk and not rebuild:
        LOG.info(f"Deleting cloudinit datasource for SOC {soc_ip} (last disk)")
        cloudinit_api = dpuagentApi.CloudinitApi(dpuagentclient)
        try:
            res = cloudinit_api.delete_cloudinit_dpu_agent_v1_cloudinit_delete_post()
            if res.code != 0:
                LOG.warning(f"Failed to delete cloudinit datasource for SOC {soc_ip}, "
                            f"message: {res.message}")
            else:
                LOG.info(f"Successfully deleted cloudinit datasource for SOC {soc_ip}")
        except Exception as e:
            LOG.warning(f"Failed to delete cloudinit datasource for SOC {soc_ip}, error: {e}")
            cloudinit_status = 1

    # Delete virtual block device
    LOG.info(f"Deleting virtual block device for disk {disk_id}")
    blk_api = dpuagentApi.VblkApi(dpuagentclient)
    try:
        res = blk_api.delete_vblk_dpu_agent_v1_vblk_del_post(
            dpuagent_api_v1_schemas_vblk_schemas_delete_request={
                "rbd_path": data.rbd_path,
                "gw_pwd": "yunsilicon",
                "gw_ip": data.mon_hosts,
                "force": True,
                "bootable": True,
                "gw_user": "admin",
                "uuid": data.uuid})
        LOG.info("Virtual block device deletion response for disk "
                 f"{disk_id}: code={res.code}, message={res.message}")
    except Exception as e:
        LOG.error(f"Failed to delete virtblk for disk {disk_id} in {soc_ip}, error: {e}")
        raise exceptions.VblkDeleteException(str(e))

    if res.code != 0:
        LOG.error(
            f"Failed to delete virtblk for disk {disk_id} in {soc_ip}, message: {res.message}")
        raise exceptions.VblkDeleteException(res.message)

    LOG.info(f"Successfully deleted virtual block device for disk {disk_id}")

    # Save checkpoint after deletion
    LOG.info(f"Saving checkpoint after deleting disk {disk_id}")
    try:
        recoverapi = dpuagentApi.RecoveryApi(dpuagentclient)
        res = recoverapi.save_checkpoint_dpu_agent_v1_checkpoint_save_post()
        if res.code != 0:
            LOG.error(f"Failed to save checkpoint after deleting disk {disk_id}: {res.message}")
            raise exceptions.CheckPointSaveException(res.message)
        LOG.info(f"Successfully saved checkpoint after deleting disk {disk_id}")
    except Exception as e:
        LOG.error(f"Failed to save checkpoint after deleting block {disk_id}: {e}")
        raise

    # Delete RBD image
    LOG.info(f"Deleting RBD image for disk {disk_id}")
    for mon_host in data.mon_hosts.split(","):
        try:
            cephclient = get_cephclient(mon_host)
            ceph_api.RbdApi(cephclient).api_block_image_image_spec_delete(
                image_spec=quote(data.rbd_path, safe=""))
            LOG.info(f"Successfully deleted RBD image for disk {disk_id}")
            break
        except Exception as e:
            LOG.error(f"Failed to delete RBD image for system disk {disk_id} on mon_host {mon_host}"
                      f", error: {e}")

    else:
        msg = f"Failed to delete rbd for system disk {disk_id}"
        LOG.error(msg)
        raise exceptions.DeleteSystemdiskException(msg)

    LOG.info(f"Successfully completed deletion of system disk {disk_id}")

    server = db.find_one(SERVER_COLLECTION, {"id": data.bare_id})
    if not server:
        LOG.warning(f"Server {data.bare_id} not found for boot entries query")
        raise HTTPException(status_code=404, detail="bare metal not found")

    # Try to cleanup orphaned EFI entries, but capture errors
    if server["device"].get("username") and server["device"].get("password"):
        try:
            cleanup_orphaned_efi_entries(
                server["device"].get("ip"), server["device"].get("username"),
                server["device"].get("password")
            )
            LOG.info(f"EFI cleanup succeeded for server {server['id']}")
        except Exception as e:
            LOG.warning(
                f"EFI cleanup failed for server {server['id']}: {e}. "
                "Frontend will be notified with special code."
            )
            efi_status = 1
    else:
        LOG.warning(
            f"Skipping EFI cleanup for server {server['id']} due to missing credentials"
        )
        efi_status = 1

    # Return final result to frontend
    return {"efi_status": efi_status, "cloudinit_status": cloudinit_status}


@router.post("/mv-servers/{server_id}/system-disks/delete", status_code=status.HTTP_202_ACCEPTED,
             response_model=mv200_schemas.SystemDiskCreateResponse)
async def delete_system_disk(server_id: str, data: mv200_schemas.SystemDiskDeleteRequest):
    """
    Delete system disk by ID
    """
    LOG.info(f"Received request to delete system disk on mv200 {server_id}")
    try:
        result = await _delete_system_disk(server_id, data)
        LOG.info(f"Successfully completed deletion request on mv200 {server_id}")
        return result
    except Exception as e:
        LOG.error(f"Failed to complete deletion request on mv200 {server_id}: {e}")
        raise


async def cleanup_orphaned_efi_entries(host_ip: str, username: str, password: str) -> list:
    """
    Cleanup orphaned EFI boot entries. These are entries whose GPT UUID does not exist.

    Args:
        host_ip: Physical host IP
        username: SSH username
        password: SSH password

    Returns:
        list: Deleted boot entries with boot number and GPT UUID
    """
    LOG.info(f"Cleaning up orphaned EFI boot entries on host {host_ip}")
    deleted_entries = []

    try:
        # Get existing GPT UUIDs from the system
        existing_uuids_output = await ssh_execute_async(host_ip, 
                                                        "lsblk -no PARTUUID | grep -v '^$'", 
                                                        username, password)
        existing_uuids = set(existing_uuids_output.splitlines())
        LOG.info(f"Existing PARTUUIDs: {existing_uuids}")

        # Get all EFI boot entries
        efi_entries_output = await ssh_execute_async(host_ip, "efibootmgr -v", username, password)

        for line in efi_entries_output.splitlines():
            if line.startswith("Boot") and "*" in line:
                boot_num = line.split()[0].replace("Boot", "").replace("*", "")
                # Extract GPT UUID from HD(...,GPT,<UUID>,...) format
                gpt_match = re.search(r'GPT,([a-f0-9-]+)', line)
                if gpt_match:
                    gpt_uuid = gpt_match.group(1)
                    # If GPT UUID is not present on the system, delete the entry
                    if gpt_uuid not in existing_uuids:
                        LOG.info(f"Found orphaned boot entry {boot_num} with GPT UUID {gpt_uuid}")
                        try:
                            await ssh_execute_async(
                                host_ip, f"efibootmgr -b {boot_num} -B", username, password)
                            deleted_entries.append({"boot_num": boot_num, "gpt_uuid": gpt_uuid})
                            LOG.info(f"Deleted orphaned EFI boot entry {boot_num}")
                        except Exception as e:
                            LOG.error(f"Failed to delete boot entry {boot_num}: {e}")

        LOG.info(f"Cleaned up {len(deleted_entries)} orphaned EFI entries")

    except Exception as e:
        LOG.error(f"Failed to cleanup orphaned EFI entries on {host_ip}: {e}")
        raise

    return deleted_entries


@router.delete("/mv-servers/{server_id}/cloud-init", status_code=status.HTTP_202_ACCEPTED)
async def delete_cloud_init_datasource(server_id: str):

    try:
        mv200 = db.find_one(MV_SERVER_COLLECTION, {"id": server_id})
    except Exception:
        LOG.warning(f"mv200 {server_id} not found")
        raise HTTPException(status_code=404, detail="mv200 not found")

    mv200_ip = mv200["ip_address"]
    LOG.info(f"Fetching cloud disk for {mv200_ip}")

    try:
        dpuagentclient = get_dpuagentclient(mv200_ip)
        res = dpuagentApi.CloudinitApi(
            dpuagentclient).delete_cloudinit_dpu_agent_v1_cloudinit_delete_post()
        if res.code != 0:
            LOG.error("Failed to delete cloudinit datasource")
            raise exceptions.CheckPointSaveException(res.message)
        LOG.info("Successfully deleted cloudinit datasource")

    except Exception as e:
        LOG.error(f"Failed to delete cloud init datasource , error: {e}")

    LOG.info("Saving checkpoint after deleting cloudinit datasource")
    try:
        recoverapi = dpuagentApi.RecoveryApi(dpuagentclient)
        res = recoverapi.save_checkpoint_dpu_agent_v1_checkpoint_save_post()
        if res.code != 0:
            LOG.error(
                f"Failed to save checkpoint after deleting cloudinit datasource: {res.message}")
            raise exceptions.CheckPointSaveException(res.message)
        LOG.info("Successfully saved checkpoint after deleting cloudinit datasource")
    except Exception as e:
        LOG.warning(f"Failed to save checkpoint after deleting cloudinit datasource, error: {e}")
