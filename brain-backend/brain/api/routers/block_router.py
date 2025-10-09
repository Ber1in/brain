# Copyright (C) 2021 - 2025, Shanghai Yunsilicon Technology Co., Ltd.
# All rights reserved.

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
import logging
import uuid
from urllib.parse import quote

from brain.api.schemas import block_schemas
from brain.auth import authenticate_user
from brain import exceptions
from brain.json_db import JSONDocumentDB
from brain.utils import get_cephclient, get_dpuagentclient
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


async def _create_system_disk(data: block_schemas.BareMetalCreate, cloudinit=True):
    disk_data = data.system_disk
    # Check if image exists
    image = db.find_one(IMAGE_COLLECTION, {"id": disk_data.image_id})
    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image '{disk_data.image_id}' not found"
        )

    # Check if MV200 server exists
    mv_server = db.find_one(MV_SERVER_COLLECTION, {"id": disk_data.mv200_id})
    if not mv_server:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MV200 server '{disk_data.mv200_id}' not found"
        )

    baremetal = db.find_one(BARE_METAL_SERVER_COLLECTION, {"id": mv_server.get("bare_id")})
    if not baremetal:
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

    # Check if RBD path already exists (should be unique due to UUID)
    existing_rbd = db.find(SYSTEM_DISK_COLLECTION, {"rbd_path": rbd_path})
    if existing_rbd:
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
        rbd_api = ceph_api.RbdApi(cephclient)
        if disk_data.flatten:
            rbd_api.api_block_image_image_spec_flatten_post(
                image_spec=quote(f"{RBD_POOL}/{disk_id}", safe=""))
        rbd_api.api_block_image_image_spec_put(
            image_spec=quote(f"{RBD_POOL}/{disk_id}", safe=""),
            api_block_image_image_spec_put_request={"size": disk_data.size_gb * 1024 * 1024 * 1024}
        )
    except Exception as e:
        LOG.error(f"Failed to clone system disk {disk_id}, error: {e}")
        raise

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
    except Exception as e:
        LOG.error(f"Failed to create virtblk in {soc_ip}, error: {e}")
        raise exceptions.VblkCreateException(str(e))
    if res.code != 0:
        LOG.error(f"Failed to create virtblk in {soc_ip}, message: {res.message}")
        raise exceptions.VblkCreateException(res.message)

    disk_dict["blk_id"] = res.uuid
    # Set system user
    if cloudinit:
        system_user = data.system_user
        user_data = {"users": [{"name": system_user.name,
                               "password": system_user.password}]}

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
                LOG.warning(f"Failed to create cloudinit datasource for SOC {soc_ip},"
                            f" message: {res.message}")
        except Exception as e:
            LOG.error(f"Failed to create cloudinit datasource for SOC {soc_ip}, error: {e}")

    try:
        recoverapi = dpuagent_api.RecoveryApi(dpuagentclient)
        res = recoverapi.save_checkpoint_dpu_agent_v1_checkpoint_save_post()
        if res.code != 0:
            raise exceptions.CheckPointSaveException(res.message)
    except Exception as e:
        LOG.error(f"Failed to save checkpoint after create block {disk_id}: {e}")

    # Insert new system disk
    db.insert(SYSTEM_DISK_COLLECTION, disk_dict)

    return disk_dict


async def _delete_system_disk(disk_id):
    # Check if disk exists
    existing_disks = db.find_one(SYSTEM_DISK_COLLECTION, {"id": disk_id})
    if not existing_disks:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="System disk not found"
        )

    soc_ip = existing_disks["mv200_ip"]
    mon_host = existing_disks["mon_host"]

    dpuagentclient = get_dpuagentclient(soc_ip)

    disks_with_same_ip = db.find(SYSTEM_DISK_COLLECTION, {"mv200_ip": soc_ip})
    is_last_disk = len(disks_with_same_ip) == 1

    if is_last_disk:
        cloudinit_api = dpuagent_api.CloudinitApi(dpuagentclient)
        try:
            res = cloudinit_api.delete_cloudinit_dpu_agent_v1_cloudinit_delete_post()
            if res.code != 0:
                LOG.warning(f"Failed to delete cloudinit datasource for SOC {soc_ip}, "
                            f"message: {res.message}")
        except Exception as e:
            LOG.warning(f"Failed to delete cloudinit datasource for SOC {soc_ip}, error: {e}")

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
    except Exception as e:
        LOG.error(f"Failed to delete virtblk in {soc_ip}, error: {e}")
        raise exceptions.VblkDeleteException(str(e))
    if res.code != 0:
        LOG.error(f"Failed to delete virtblk in {soc_ip}, message: {res.message}")
        raise exceptions.VblkDeleteException(res.message)

    try:
        recoverapi = dpuagent_api.RecoveryApi(dpuagentclient)
        res = recoverapi.save_checkpoint_dpu_agent_v1_checkpoint_save_post()
        if res.code != 0:
            raise exceptions.CheckPointSaveException(res.message)
    except Exception as e:
        LOG.error(f"Failed to save checkpoint after delete block {disk_id}: {e}")

    try:
        cephclient = get_cephclient(mon_host)
        ceph_api.RbdApi(cephclient).api_block_image_image_spec_delete(
            image_spec=quote(existing_disks["rbd_path"], safe=""))
    except Exception as e:
        LOG.error(f"Failed to delete system disk {disk_id}, error: {e}")
        raise

    # Delete disk record from database
    deleted_count = db.delete(SYSTEM_DISK_COLLECTION, {"id": disk_id})
    if deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="System disk not found"
        )


@router.post("/system-disks", response_model=block_schemas.SystemDisk,
             status_code=status.HTTP_201_CREATED)
async def create_system_disk(data: block_schemas.BareMetalCreate):
    """
    Create a new system disk RBD from image for specific MV200 server
    """
    return await _create_system_disk(data)


@router.get("/system-disks", response_model=List[block_schemas.SystemDisk])
async def get_all_system_disks():
    """
    Get all system disks list
    """
    try:
        disks = db.find(SYSTEM_DISK_COLLECTION, {})
        # Return all disks with their data (excluding mon_host and rbd_path)
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
    try:
        disk = db.find_one(SYSTEM_DISK_COLLECTION, {"id": disk_id})
        if not disk:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="System disk not found"
            )

        # Return disk information (excluding mon_host and rbd_path)
        return disk
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
    try:
        # Check if disk exists
        existing_disks = db.find(SYSTEM_DISK_COLLECTION, {"id": disk_id})
        if not existing_disks:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="System disk not found"
            )

        update_dict = {k: v for k, v in update_data.dict(exclude_unset=True).items()}

        if update_dict:
            db.update_one(SYSTEM_DISK_COLLECTION, {"id": disk_id}, update_dict)
        # Return updated disk information (excluding mon_host and rbd_path)
        updated_disks = db.find(SYSTEM_DISK_COLLECTION, {"id": disk_id})
        updated_disk = updated_disks[0]
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
    await _delete_system_disk(disk_id)


@router.post("/system-disks/{disk_id}/upload", status_code=status.HTTP_202_ACCEPTED)
async def save_block_to_new_image(disk_id: str, data: block_schemas.UploadToImage):
    # Check if disk exists
    existing_disk = db.find_one(SYSTEM_DISK_COLLECTION, {"id": disk_id})
    if not existing_disk:
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

    existing_image = db.find(IMAGE_COLLECTION, {"name": data.dest_name,
                                                "mon_host": mon_host})
    if existing_image:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Image with this name already exists in ceph cluster {mon_host}"
        )

    # Check if ceph location already exists
    existing_location = db.find(IMAGE_COLLECTION, {
        "ceph_location": ceph_location, "mon_host": mon_host})
    if existing_location:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=("Image with this ceph location already exists"
                    f" in ceph cluster {mon_host}")
        )

    try:
        rbd_api.api_block_image_image_spec_copy_post(
            image_spec=quote(existing_disk["rbd_path"], safe=""),
            api_block_image_image_spec_copy_post_request={
                "dest_image_name": dest_name,
                "dest_namespace": "",
                "dest_pool_name": dest_pool
            })
    except Exception as e:
        LOG.error(f"Failed to copy system disk {disk_id}, error: {e}")
        raise

    image_dict = {
        "id": image_id,
        "name": dest_name,
        "ceph_location": ceph_location,
        "min_size": existing_disk["size_gb"],
        "mon_host": mon_host,
        "description": data.description,
        "brain": True
    }

    try:
        snap_api = ceph_api.RbdSnapshotApi(ceph_client)
        snap_api.api_block_image_image_spec_snap_post(
            image_spec=quote(ceph_location, safe=""),
            api_block_image_image_spec_snap_post_request={"snapshot_name": SNAP_NAME,
                                                          "mirrorImageSnapshot": False})
        snap_api.api_block_image_image_spec_snap_snapshot_name_put(
            image_spec=quote(ceph_location, safe=""),
            snapshot_name=SNAP_NAME,
            api_block_image_image_spec_snap_snapshot_name_put_request={"is_protected": True})
    except ApiException as e:
        LOG.error(f"Failed to create snapshot {SNAP_NAME} of the rbd "
                  f"{ceph_location}: {str(e)}")
        raise
    else:
        # Insert new image
        db.insert(IMAGE_COLLECTION, image_dict)

    # Return the created image information
    return image_dict


@router.post("/system-disks/{disk_id}/rebuild", response_model=block_schemas.SystemDisk,
             status_code=status.HTTP_202_ACCEPTED)
async def rebuild_block_to_dest_image(disk_id: str, image_id: str):
    existing_disk = db.find_one(SYSTEM_DISK_COLLECTION, {"id": disk_id})
    if not existing_disk:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source system disk not found"
        )
    rebuild_data = block_schemas.BareMetalCreate(
        system_disk=block_schemas.SystemDiskCreate(
            image_id=image_id,
            mv200_id=existing_disk["mv200_id"],
            size_gb=existing_disk["size_gb"],
            flatten=existing_disk["flatten"],
            description=f"Rebuilt from {disk_id} - {existing_disk.get('description', '')}"
        ),
        # system_user will not be used because the cloudinit datasource will not be recreated
        system_user=block_schemas.SystemUser(
            name="root",
            password="password"
        )
    )
    await _delete_system_disk(disk_id)
    return await _create_system_disk(rebuild_data, cloudinit=False)