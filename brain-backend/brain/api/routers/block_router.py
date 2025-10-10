# Copyright (C) 2021 - 2025, Shanghai Yunsilicon Technology Co., Ltd.
# All rights reserved.

import re
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
import logging
import uuid
from urllib.parse import quote

from brain.api.schemas import block_schemas
from brain.auth import authenticate_user
from brain import exceptions
from brain.json_db import JSONDocumentDB
from brain.utils import get_cephclient, get_dpuagentclient, ssh_execute
from brain.clients.ceph import api as ceph_api
from brain.clients.dpuagent import api as dpuagent_api
from brain.clients.ceph.exceptions import ApiException

router = APIRouter(dependencies=[Depends(authenticate_user)])
LOG = logging.getLogger(__name__)
db = JSONDocumentDB()

# Collection names
SYSTEM_DISK_COLLECTION = "system_disks"
IMAGE_COLLECTION = "images"
MV_SERVER_COLLECTION = "mv_servers"
BARE_METAL_SERVER_COLLECTION = "bare_metals"

# Constants
RBD_POOL = "compute"
IMAGE_POOL = "images"
SNAP_NAME = "brain_snap"


async def _create_system_disk(data: block_schemas.BareMetalCreate, rebuild=False):
    disk_data = data.system_disk
    LOG.info(f"Starting system disk creation process for image {disk_data.image_id} "
             f"on MV200 server {disk_data.mv200_id}")

    # Check if image exists
    image = db.find_one(IMAGE_COLLECTION, {"id": disk_data.image_id})
    if not image:
        LOG.warning(f"Image '{disk_data.image_id}' not found when creating system disk")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image '{disk_data.image_id}' not found"
        )

    # Check if MV200 server exists
    mv_server = db.find_one(MV_SERVER_COLLECTION, {"id": disk_data.mv200_id})
    if not mv_server:
        LOG.warning(f"MV200 server '{disk_data.mv200_id}' not found when creating system disk")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MV200 server '{disk_data.mv200_id}' not found"
        )

    baremetal = db.find_one(BARE_METAL_SERVER_COLLECTION, {"id": mv_server.get("bare_id")})
    if not baremetal:
        LOG.warning(f"Bare Metal server {mv_server.get('bare_id')} not"
                    f" found for MV200 {disk_data.mv200_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bare Metal server {mv_server.get('bare_id')} not found"
        )

    # Generate unique ID and RBD path
    mon_host = image.get("mon_host")
    soc_ip = mv_server.get("ip_address")
    host_ip = baremetal.get("host_ip")
    gateway = baremetal.get("gateway")
    mac = baremetal.get("mac")
    disk_id = str(uuid.uuid4())
    rbd_path = f"{RBD_POOL}/{disk_id}"

    LOG.info(f"Generated disk ID: {disk_id}, RBD path: {rbd_path}, "
             f"mon_host: {mon_host}, soc_ip: {soc_ip}")

    # Check if RBD path already exists (should be unique due to UUID)
    existing_rbd = db.find(SYSTEM_DISK_COLLECTION, {"rbd_path": rbd_path})
    if existing_rbd:
        LOG.error(f"UUID conflict: RBD path {rbd_path} already exists")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Generated RBD path already exists (UUID conflict)"
        )

    # Create disk document
    disk_dict = {
        "id": disk_id,
        "rbd_path": rbd_path,
        "image_id": disk_data.image_id,
        "mv200_id": disk_data.mv200_id,
        "mv200_ip": soc_ip,
        "mon_host": mon_host,
        "size_gb": disk_data.size_gb,
        "flatten": disk_data.flatten,
        "description": disk_data.description
    }

    try:
        LOG.info(
            f"Starting RBD clone process for disk {disk_id} from image {image['ceph_location']}")
        cephclient = get_cephclient(mon_host)
        ceph_api.RbdSnapshotApi(
            cephclient).api_block_image_image_spec_snap_snapshot_name_clone_post(
            image_spec=quote(image["ceph_location"], safe=""),
                snapshot_name=SNAP_NAME,
            api_block_image_image_spec_snap_snapshot_name_clone_post_request={
                "child_pool_name": RBD_POOL,
                "child_image_name": disk_id
            }
        )
        LOG.info(f"Successfully cloned RBD image for disk {disk_id}")

        rbd_api = ceph_api.RbdApi(cephclient)
        if disk_data.flatten:
            LOG.info(f"Flattening RBD image for disk {disk_id}")
            rbd_api.api_block_image_image_spec_flatten_post(
                image_spec=quote(f"{RBD_POOL}/{disk_id}", safe=""))
            LOG.info(f"Successfully flattened RBD image for disk {disk_id}")

        LOG.info(f"Resizing RBD image for disk {disk_id} to {disk_data.size_gb}GB")
        rbd_api.api_block_image_image_spec_put(
            image_spec=quote(f"{RBD_POOL}/{disk_id}", safe=""),
            api_block_image_image_spec_put_request={"size": disk_data.size_gb * 1024 * 1024 * 1024}
        )
        LOG.info(f"Successfully resized RBD image for disk {disk_id}")

    except Exception as e:
        LOG.error(f"Failed to clone system disk {disk_id}, error: {e}")
        raise

    # Create virtual block device
    LOG.info(f"Creating virtual block device for disk {disk_id} on SOC {soc_ip}")
    dpuagentclient = get_dpuagentclient(soc_ip)
    blk_api = dpuagent_api.VblkApi(dpuagentclient)
    try:
        res = blk_api.create_vblk_dpu_agent_v1_vblk_add_post(
            dpuagent_api_v1_schemas_vblk_schemas_create_request={
                "rbd_path": f"{RBD_POOL}/{disk_id}",
                "gw_pwd": "yunsilicon",
                "gws": [mon_host],
                "vq_count": 2,
                "vq_size": 512,
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

    disk_dict["blk_id"] = res.uuid
    LOG.info(f"Successfully created virtual block device for disk {disk_id} with UUID: {res.uuid}")

    cloudinit_status = 0
    # Set system user and cloudinit configuration
    if not rebuild:
        LOG.info(f"Configuring cloudinit for disk {disk_id}")
        system_user = data.system_user
        user_data = {"users": [{"name": system_user.name,
                                "password": system_user.password}]}
        if baremetal.get("name"):
            user_data["hostname"] = baremetal.get("name")

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
                    "nameservers": [
                        "10.0.0.50",
                        "10.0.0.51"
                    ],
                }
            ]
        }
        try:
            cloudinit_api = dpuagent_api.CloudinitApi(dpuagentclient)
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
        recoverapi = dpuagent_api.RecoveryApi(dpuagentclient)
        res = recoverapi.save_checkpoint_dpu_agent_v1_checkpoint_save_post()
        if res.code != 0:
            LOG.error(f"Failed to save checkpoint for disk {disk_id}: {res.message}")
            raise exceptions.CheckPointSaveException(res.message)
        LOG.info(f"Successfully saved checkpoint for disk {disk_id}")
    except Exception as e:
        LOG.error(f"Failed to save checkpoint after creating block {disk_id}: {e}")
        raise

    # Insert new system disk to database
    LOG.info(f"Inserting disk {disk_id} into database")
    db.insert(SYSTEM_DISK_COLLECTION, disk_dict)
    LOG.info(f"Successfully created system disk {disk_id}")

    efi_status = 0
    if baremetal.get("os_user") and baremetal.get("os_password"):
        try:
            create_efi_boot_entry(host_ip, "root", "ymxl@2021", 40, disk_id, image["name"])
            LOG.info(f"EFI create succeeded for server {baremetal['id']}")
        except Exception as e:
            LOG.warning(
                f"EFI create failed for server {baremetal['id']}: {e}. "
                "Frontend will be notified with special code."
            )
            efi_status = 1
    else:
        LOG.warning(
            f"Skipping EFI creating for server {baremetal['id']} due to missing credentials"
        )
        efi_status = 1

    return {"efi_status": efi_status, "cloudinit_status": cloudinit_status}


async def _delete_system_disk(disk_id, rebuild=False):
    LOG.info(f"Starting deletion process for system disk {disk_id}")

    # Check if disk exists
    existing_disks = db.find_one(SYSTEM_DISK_COLLECTION, {"id": disk_id})
    if not existing_disks:
        LOG.warning(f"System disk {disk_id} not found during deletion")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="System disk not found"
        )

    soc_ip = existing_disks["mv200_ip"]
    mon_host = existing_disks["mon_host"]
    LOG.info(f"Found disk {disk_id} with SOC IP: {soc_ip}, mon_host: {mon_host}")

    dpuagentclient = get_dpuagentclient(soc_ip)

    # Check if this is the last disk on the SOC
    disks_with_same_ip = db.find(SYSTEM_DISK_COLLECTION, {"mv200_ip": soc_ip})
    is_last_disk = len(disks_with_same_ip) == 1
    LOG.info(f"Disk {disk_id} is {'last' if is_last_disk else 'not last'} disk on SOC {soc_ip}")

    efi_status = 0
    cloudinit_status = 0
    if is_last_disk and not rebuild:
        LOG.info(f"Deleting cloudinit datasource for SOC {soc_ip} (last disk)")
        cloudinit_api = dpuagent_api.CloudinitApi(dpuagentclient)
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
    blk_api = dpuagent_api.VblkApi(dpuagentclient)
    try:
        res = blk_api.delete_vblk_dpu_agent_v1_vblk_del_post(
            dpuagent_api_v1_schemas_vblk_schemas_delete_request={
                "rbd_path": f"{RBD_POOL}/{disk_id}",
                "gw_pwd": "yunsilicon",
                "gw_ip": mon_host,
                "force": True,
                "bootable": True,
                "gw_user": "admin",
                "uuid": existing_disks["blk_id"]})
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
        recoverapi = dpuagent_api.RecoveryApi(dpuagentclient)
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
    try:
        cephclient = get_cephclient(mon_host)
        ceph_api.RbdApi(cephclient).api_block_image_image_spec_delete(
            image_spec=quote(existing_disks["rbd_path"], safe=""))
        LOG.info(f"Successfully deleted RBD image for disk {disk_id}")
    except Exception as e:
        LOG.error(f"Failed to delete RBD image for system disk {disk_id}, error: {e}")
        raise

    # Delete disk record from database
    LOG.info(f"Deleting disk {disk_id} record from database")
    deleted_count = db.delete(SYSTEM_DISK_COLLECTION, {"id": disk_id})
    if deleted_count == 0:
        LOG.error(f"Failed to delete disk {disk_id} record from database")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="System disk not found"
        )

    LOG.info(f"Successfully completed deletion of system disk {disk_id}")
    mv_server = db.find_one(MV_SERVER_COLLECTION, {"id": existing_disks["mv200_id"]})
    if not mv_server:
        LOG.warning(
            f"MV200 server {existing_disks['mv200_id']} not found when creating system disk"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MV200 server {existing_disks['mv200_id']} not found"
        )

    server = db.find_one(BARE_METAL_SERVER_COLLECTION, {"id": mv_server["bare_id"]})
    if not server:
        LOG.warning(f"Server {mv_server['bare_id']} not found for boot entries query")
        raise HTTPException(status_code=404, detail="bare metal not found")

    # Try to cleanup orphaned EFI entries, but capture errors
    if server.get("os_user") and server.get("os_password"):
        try:
            cleanup_orphaned_efi_entries(
                server.get("host_ip"), server.get("os_user"), server.get("os_password")
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


@router.post("/system-disks", status_code=status.HTTP_201_CREATED)
async def create_system_disk(data: block_schemas.BareMetalCreate):
    """
    Create a new system disk RBD from image for specific MV200 server
    """
    LOG.info(f"Received request to create system disk for MV200 {data.system_disk.mv200_id} "
             f"with image {data.system_disk.image_id}")
    try:
        result = await _create_system_disk(data)
        LOG.info(f"Successfully completed system disk creation request "
                 f"with image {data.system_disk.image_id}")
        return result
    except Exception as e:
        LOG.error(f"Failed to complete system disk creation request: {e}")
        raise


@router.get("/system-disks", response_model=List[block_schemas.SystemDisk])
async def get_all_system_disks():
    """
    Get all system disks list
    """
    LOG.info("Received request to get all system disks")
    try:
        disks = db.find(SYSTEM_DISK_COLLECTION, {})
        LOG.info(f"Retrieved {len(disks)} system disks from database")
        return disks
    except Exception as e:
        LOG.error(f"Failed to get system disks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get system disks"
        )


@router.get("/system-disks/{disk_id}", response_model=block_schemas.SystemDisk)
async def get_system_disk(disk_id: str):
    """
    Get specific system disk by ID
    """
    LOG.info(f"Received request to get system disk {disk_id}")
    try:
        disk = db.find_one(SYSTEM_DISK_COLLECTION, {"id": disk_id})
        if not disk:
            LOG.warning(f"System disk {disk_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="System disk not found"
            )

        LOG.info(f"Successfully retrieved system disk {disk_id}")
        return disk
    except HTTPException:
        raise
    except Exception as e:
        LOG.error(f"Failed to get system disk {disk_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get system disk"
        )


@router.put("/system-disks/{disk_id}", response_model=block_schemas.SystemDisk)
async def update_system_disk(disk_id: str, update_data: block_schemas.SystemDiskUpdate):
    """
    Update system disk information by ID
    """
    LOG.info(f"Received request to update system disk {disk_id} with data: {update_data.dict()}")
    try:
        # Check if disk exists
        existing_disks = db.find(SYSTEM_DISK_COLLECTION, {"id": disk_id})
        if not existing_disks:
            LOG.warning(f"System disk {disk_id} not found for update")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="System disk not found"
            )

        update_dict = {k: v for k, v in update_data.dict(exclude_unset=True).items()}
        LOG.info(f"Updating system disk {disk_id} with fields: {list(update_dict.keys())}")

        if update_dict:
            db.update_one(SYSTEM_DISK_COLLECTION, {"id": disk_id}, update_dict)
            LOG.info(f"Successfully updated system disk {disk_id} in database")
        else:
            LOG.info(f"No fields to update for system disk {disk_id}")

        # Return updated disk information
        updated_disks = db.find(SYSTEM_DISK_COLLECTION, {"id": disk_id})
        updated_disk = updated_disks[0]
        LOG.info(f"Successfully completed update for system disk {disk_id}")
        return updated_disk

    except HTTPException:
        raise
    except Exception as e:
        LOG.error(f"Failed to update system disk {disk_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update system disk"
        )


@router.delete("/system-disks/{disk_id}", status_code=status.HTTP_202_ACCEPTED)
async def delete_system_disk(disk_id: str):
    """
    Delete system disk by ID
    """
    LOG.info(f"Received request to delete system disk {disk_id}")
    try:
        await _delete_system_disk(disk_id)
        LOG.info(f"Successfully completed deletion request for system disk {disk_id}")
    except Exception as e:
        LOG.error(f"Failed to complete deletion request for system disk {disk_id}: {e}")
        raise


@router.post("/system-disks/{disk_id}/upload", status_code=status.HTTP_202_ACCEPTED)
async def save_block_to_new_image(disk_id: str, data: block_schemas.UploadToImage):
    """
    Upload system disk to new image
    """
    LOG.info(
        f"Received request to upload system disk {disk_id} to new image with data: {data.dict()}")

    # Check if disk exists
    existing_disk = db.find_one(SYSTEM_DISK_COLLECTION, {"id": disk_id})
    if not existing_disk:
        LOG.warning(f"System disk {disk_id} not found for upload to image")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="System disk not found"
        )

    mon_host = existing_disk["mon_host"]
    ceph_client = get_cephclient(mon_host)
    rbd_api = ceph_api.RbdApi(ceph_client)
    image_id = str(uuid.uuid4())
    dest_name = data.dest_name if data.dest_name is not None else image_id
    dest_pool = data.dest_pool if data.dest_pool is not None else IMAGE_POOL
    ceph_location = f'{dest_pool}/{dest_name}'

    LOG.info(f"Creating new image from disk {disk_id}: name={dest_name}, pool={dest_pool}, "
             f"ceph_location={ceph_location}")

    # Check if image name already exists
    existing_image = db.find(IMAGE_COLLECTION, {"name": data.dest_name,
                                                "mon_host": mon_host})
    if existing_image:
        LOG.warning(f"Image with name {data.dest_name} already exists in ceph cluster {mon_host}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Image with this name already exists in ceph cluster {mon_host}"
        )

    # Check if ceph location already exists
    existing_location = db.find(IMAGE_COLLECTION, {
        "ceph_location": ceph_location, "mon_host": mon_host})
    if existing_location:
        LOG.warning(
            f"Image with ceph location {ceph_location} already exists in ceph cluster {mon_host}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=("Image with this ceph location already exists"
                    f" in ceph cluster {mon_host}")
        )

    # Copy RBD image
    try:
        LOG.info(f"Starting RBD copy from {existing_disk['rbd_path']} to {ceph_location}")
        rbd_api.api_block_image_image_spec_copy_post(
            image_spec=quote(existing_disk["rbd_path"], safe=""),
            api_block_image_image_spec_copy_post_request={
                "dest_image_name": dest_name,
                "dest_namespace": "",
                "dest_pool_name": dest_pool
            })
        LOG.info(f"Successfully copied RBD image to {ceph_location}")
    except Exception as e:
        LOG.error(f"Failed to copy system disk {disk_id} to {ceph_location}, error: {e}")
        raise

    # Create image record
    image_dict = {
        "id": image_id,
        "name": dest_name,
        "ceph_location": ceph_location,
        "min_size": existing_disk["size_gb"],
        "mon_host": mon_host,
        "description": data.description,
        "brain": True
    }

    # Create snapshot
    try:
        LOG.info(f"Creating snapshot {SNAP_NAME} for new image {ceph_location}")
        snap_api = ceph_api.RbdSnapshotApi(ceph_client)
        snap_api.api_block_image_image_spec_snap_post(
            image_spec=quote(ceph_location, safe=""),
            api_block_image_image_spec_snap_post_request={"snapshot_name": SNAP_NAME,
                                                          "mirrorImageSnapshot": False})
        snap_api.api_block_image_image_spec_snap_snapshot_name_put(
            image_spec=quote(ceph_location, safe=""),
            snapshot_name=SNAP_NAME,
            api_block_image_image_spec_snap_snapshot_name_put_request={"is_protected": True})
        LOG.info(f"Successfully created and protected snapshot {SNAP_NAME} for {ceph_location}")
    except ApiException as e:
        LOG.error(f"Failed to create snapshot {SNAP_NAME} of the rbd {ceph_location}: {str(e)}")
        raise
    else:
        # Insert new image to database
        LOG.info(f"Inserting new image {image_id} into database")
        db.insert(IMAGE_COLLECTION, image_dict)
        LOG.info(f"Successfully created new image {image_id} from disk {disk_id}")

    # Return the created image information
    return image_dict


@router.post("/system-disks/{disk_id}/rebuild", status_code=status.HTTP_202_ACCEPTED)
async def rebuild_block_to_dest_image(disk_id: str, image_id: str):
    """
    Rebuild system disk to destination image
    """
    LOG.info(f"Received request to rebuild system disk {disk_id} with image {image_id}")

    existing_disk = db.find_one(SYSTEM_DISK_COLLECTION, {"id": disk_id})
    if not existing_disk:
        LOG.warning(f"Source system disk {disk_id} not found for rebuild")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source system disk not found"
        )

    LOG.info(f"Rebuilding disk {disk_id} from existing disk: MV200={existing_disk['mv200_id']}, "
             f"size={existing_disk['size_gb']}GB")

    rebuild_data = block_schemas.BareMetalCreate(
        system_disk=block_schemas.SystemDiskCreate(
            image_id=image_id,
            mv200_id=existing_disk["mv200_id"],
            size_gb=existing_disk["size_gb"],
            flatten=existing_disk["flatten"],
            description=existing_disk.get('description', '')
        ),
        # system_user will not be used because the cloudinit datasource will not be recreated
        system_user=block_schemas.SystemUser(
            name="root",
            password="password"
        )
    )

    await _delete_system_disk(disk_id, rebuild=True)
    result = await _create_system_disk(rebuild_data, rebuild=False)
    LOG.info(f"Successfully completed rebuild of disk {disk_id} to new image {image_id}")
    return result


def create_efi_boot_entry(host_ip: str, username: str, password: str, 
                          expected_size_gb: int, disk_id: str, image_name: str) -> bool:
    """
    Create an EFI boot entry for a cloud system disk. Returns only success status.

    Args:
        host_ip: IP address of the physical host
        username: SSH username
        password: SSH password
        expected_size_gb: Expected disk size in GB
        disk_id: Disk ID used to generate the boot entry name

    Returns:
        bool: True if EFI boot entry is created or exists, False otherwise
    """
    LOG.info(f"Creating EFI boot entry for disk {disk_id} on host {host_ip}")

    try:
        # Wait for the device to be recognized
        ssh_execute(host_ip, "sleep 3", username, password)

        # Rescan PCIe devices
        ssh_execute(host_ip, "echo 1 > /sys/bus/pci/rescan", username, password)
        ssh_execute(host_ip, "sleep 2", username, password)

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
        disk_info_output = ssh_execute(host_ip, disk_info_cmd, username, password)

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
            return False

        # Select the most recently added disk
        target_device = sorted(disks, key=lambda x: x['add_time'])[-1]['name']

        # Get the first partition of the target disk
        partitions_output = ssh_execute(
            host_ip,
            f"lsblk -nlo NAME /dev/{target_device} | grep -E '{target_device}[0-9]+'",
            username, password
        )
        if not partitions_output:
            LOG.warning(f"No partitions found on /dev/{target_device}")
            return False
        target_partition = partitions_output.splitlines()[0].strip()

        # Get PARTUUID of the partition
        partuuid_output = ssh_execute(
            host_ip, f"lsblk -no PARTUUID /dev/{target_partition}", username, password
        )
        if not partuuid_output or not partuuid_output.strip():
            LOG.warning(f"No PARTUUID found for /dev/{target_partition}")
            return False
        partuuid = partuuid_output.strip()

        # Check if a boot entry already exists
        existing_entries = ssh_execute(host_ip, "efibootmgr -v", username, password)
        for line in existing_entries.splitlines():
            if partuuid in line:
                LOG.info(f"Boot entry already exists for PARTUUID {partuuid}")
                return True

        # Create a new EFI boot entry
        safe_image_name = re.sub(r'[^A-Za-z0-9-]', '-', image_name)
        boot_entry_name = f"{safe_image_name}-{disk_id[:8]}"
        efi_cmd = (
            f"efibootmgr -c -d /dev/{target_device} -p 1 -L \"{boot_entry_name}\" "
            f"-l '\\EFI\\ubuntu\\grubx64.efi'"
        )
        ssh_execute(host_ip, efi_cmd, username, password)

        # Confirm creation
        boot_entries = ssh_execute(host_ip, "efibootmgr -v", username, password)
        for line in boot_entries.splitlines():
            if boot_entry_name in line and partuuid in line:
                LOG.info(f"Created EFI boot entry for disk {disk_id}")
                return True

        LOG.warning("Failed to create EFI boot entry")
        return False

    except Exception as e:
        LOG.error(f"Failed to create EFI boot entry for disk {disk_id}: {e}")
        return False


def cleanup_orphaned_efi_entries(host_ip: str, username: str, password: str) -> list:
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
        existing_uuids_output = ssh_execute(host_ip, 
                                            "lsblk -no PARTUUID | grep -v '^$'", 
                                            username, password)
        existing_uuids = set(existing_uuids_output.splitlines())
        LOG.info(f"Existing PARTUUIDs: {existing_uuids}")

        # Get all EFI boot entries
        efi_entries_output = ssh_execute(host_ip, "efibootmgr -v", username, password)

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
                            ssh_execute(host_ip, f"efibootmgr -b {boot_num} -B", username, password)
                            deleted_entries.append({"boot_num": boot_num, "gpt_uuid": gpt_uuid})
                            LOG.info(f"Deleted orphaned EFI boot entry {boot_num}")
                        except Exception as e:
                            LOG.error(f"Failed to delete boot entry {boot_num}: {e}")

        LOG.info(f"Cleaned up {len(deleted_entries)} orphaned EFI entries")

    except Exception as e:
        LOG.error(f"Failed to cleanup orphaned EFI entries on {host_ip}: {e}")

    return deleted_entries
