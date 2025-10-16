# Copyright (C) 2021 - 2025, Shanghai Yunsilicon Technology Co., Ltd.
# All rights reserved.

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
import logging
import uuid
from urllib.parse import quote

from brain.api.schemas import image_schemas
from brain.auth import authenticate_user
from brain.utils import get_cephclient
from brain.json_db import JSONDocumentDB
from brain.clients.ceph import api
from brain.clients.ceph.exceptions import ApiException

router = APIRouter(dependencies=[Depends(authenticate_user)])
LOG = logging.getLogger(__name__)
db = JSONDocumentDB()

# Collection name
IMAGE_COLLECTION = "images"
SNAP_NAME = "brain_snap"


@router.post("/images", response_model=image_schemas.Image, 
             status_code=status.HTTP_201_CREATED)
async def create_image(image_data: image_schemas.ImageCreate):
    """
    Create a new image
    """
    LOG.info(f"Received request to create image: {image_data.name}")

    # Check if name already exists
    existing_image = db.find(IMAGE_COLLECTION, {"name": image_data.name,
                                                "mon_host": image_data.mon_host})
    if existing_image:
        LOG.warning(f"Image name {image_data.name} already exists in cluster "
                    f"{image_data.mon_host}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Image with this name already exists in ceph cluster "
            f"{image_data.mon_host}"
        )

    # Check if ceph location already exists
    existing_location = db.find(IMAGE_COLLECTION, 
                                {"ceph_location": image_data.ceph_location,
                                    "mon_host": image_data.mon_host})
    if existing_location:
        LOG.warning(f"Ceph location {image_data.ceph_location} already exists "
                    f"in cluster {image_data.mon_host}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=("Image with this ceph location already exists"
                    f" in ceph cluster {image_data.mon_host}")
        )

    # Generate unique ID and create image document
    image_id = str(uuid.uuid4())
    image_dict = {
        "id": image_id,
        "name": image_data.name,
        "ceph_location": image_data.ceph_location,
        "min_size": image_data.min_size,
        "mon_host": str(image_data.mon_host),
        "description": image_data.description,
        "brain": False
    }

    LOG.info(f"Creating image {image_id} with ceph location "
             f"{image_data.ceph_location}")
    cephclient = get_cephclient(str(image_data.mon_host))
    try:
        snap_api = api.RbdSnapshotApi(cephclient)
        LOG.info(f"Creating snapshot {SNAP_NAME} for image {image_data.ceph_location}")
        snap_api.api_block_image_image_spec_snap_post(
            image_spec=quote(image_data.ceph_location, safe=""),
            api_block_image_image_spec_snap_post_request={"snapshot_name": SNAP_NAME,
                                                          "mirrorImageSnapshot": False})
        LOG.info(f"Protecting snapshot {SNAP_NAME} for image {image_data.ceph_location}")
        snap_api.api_block_image_image_spec_snap_snapshot_name_put(
            image_spec=quote(image_data.ceph_location, safe=""),
            snapshot_name=SNAP_NAME,
            api_block_image_image_spec_snap_snapshot_name_put_request={
                "is_protected": True})
    except ApiException as e:
        LOG.error(f"Failed to create snapshot {SNAP_NAME} of the rbd "
                  f"{image_data.ceph_location}: {str(e)}")
        raise
    else:
        # Insert new image
        db.insert(IMAGE_COLLECTION, image_dict)
        LOG.info(f"Successfully created image {image_id} in database")

    LOG.info(f"Successfully completed image creation for {image_id}")
    return image_dict


@router.get("/images", response_model=List[image_schemas.Image])
async def get_all_images():
    """
    Get all images list
    """
    LOG.info("Received request to get all images")

    images = db.find(IMAGE_COLLECTION, {})
    LOG.info(f"Retrieved {len(images)} images from database")
    return images


@router.get("/images/{image_id}", response_model=image_schemas.Image)
async def get_image(image_id: str):
    """
    Get specific image by ID
    """
    LOG.info(f"Received request to get image {image_id}")

    image = db.find_one(IMAGE_COLLECTION, {"id": image_id})
    if not image:
        LOG.warning(f"Image {image_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found"
        )

    LOG.info(f"Successfully retrieved image {image_id}")
    return image


@router.put("/images/{image_id}", response_model=image_schemas.Image)
async def update_image(image_id: str, update_data: image_schemas.ImageUpdate):
    """
    Update image information by ID
    """
    LOG.info(f"Received request to update image {image_id}")

    # Check if image exists
    existing_image = db.find_one(IMAGE_COLLECTION, {"id": image_id})
    if not existing_image:
        LOG.warning(f"Image {image_id} not found for update")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found"
        )

    # If updating name, check if name conflicts with other images
    if update_data.name and update_data.name != existing_image.get("name"):
        same_name_images = db.find(IMAGE_COLLECTION, {"name": update_data.name})
        if same_name_images:
            LOG.warning(f"Image name {update_data.name} conflicts with existing image")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Another image with this name already exists"
            )

    # If updating ceph location, check if location conflicts with other images
    if update_data.ceph_location and update_data.ceph_location != existing_image.get(
            "ceph_location"):
        same_location_images = db.find(
            IMAGE_COLLECTION, {"ceph_location": update_data.ceph_location})
        if same_location_images:
            LOG.warning(f"Ceph location {update_data.ceph_location} conflicts "
                        f"with existing image")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Another image with this ceph location already exists"
            )

    # Update image information (excluding ID field)
    update_dict = {k: v for k, v in update_data.dict(
        exclude_unset=True).items() if v is not None}
    if update_dict:
        LOG.info(f"Updating image {image_id} with fields: {list(update_dict.keys())}")
        updated_count = db.update(IMAGE_COLLECTION, {"id": image_id}, update_dict)
        if updated_count == 0:
            LOG.error(f"Failed to update image {image_id} in database")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Image not found"
            )
        LOG.info(f"Successfully updated image {image_id} in database")
    else:
        LOG.info(f"No fields to update for image {image_id}")

    # Return updated image information
    updated_images = db.find(IMAGE_COLLECTION, {"id": image_id})
    updated_image = updated_images[0]
    LOG.info(f"Successfully completed update for image {image_id}")
    return updated_image


@router.delete("/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_image(image_id: str):
    """
    Delete image by ID
    """
    LOG.info(f"Received request to delete image {image_id}")
    # Check if image exists
    existing_images = db.find_one(IMAGE_COLLECTION, {"id": image_id})
    if not existing_images:
        LOG.warning(f"Image {image_id} not found for deletion")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found"
        )

    image_name = existing_images.get("name", "unknown")
    ceph_location = existing_images["ceph_location"]
    mon_host = existing_images["mon_host"]
    is_brain_image = existing_images.get("brain", False)

    LOG.info(f"Deleting image {image_id} ({image_name}) from cluster {mon_host}")
    LOG.info(f"Ceph location: {ceph_location}, Brain created: {is_brain_image}")

    cephclient = get_cephclient(mon_host)
    try:
        snap_api = api.RbdSnapshotApi(cephclient)
        LOG.info(f"Unprotecting snapshot {SNAP_NAME} for image {ceph_location}")
        snap_api.api_block_image_image_spec_snap_snapshot_name_put(
            image_spec=quote(ceph_location, safe=""),
            snapshot_name=SNAP_NAME,
            api_block_image_image_spec_snap_snapshot_name_put_request={"is_protected": False})

        LOG.info(f"Deleting snapshot {SNAP_NAME} for image {ceph_location}")
        snap_api.api_block_image_image_spec_snap_snapshot_name_delete(
            image_spec=quote(ceph_location, safe=""), 
            snapshot_name=SNAP_NAME)
    except ApiException as e:
        LOG.error(f"Failed to delete snapshot {SNAP_NAME} of the rbd "
                  f"{ceph_location}: {str(e)}")
        raise
    else:
        LOG.info(f"Snapshot {SNAP_NAME} of the rbd {ceph_location} has been deleted")

    if is_brain_image:
        try:
            LOG.info(f"Deleting RBD image {ceph_location} (Brain created image)")
            rbd_api = api.RbdApi(cephclient)
            rbd_api.api_block_image_image_spec_delete(
                image_spec=quote(ceph_location, safe=""))
            LOG.info(f"RBD {ceph_location} has been deleted because the image "
                     "was created through Brain")
        except ApiException as e:
            LOG.error(f"Failed to delete rbd {ceph_location}: {str(e)}")
            raise
    else:
        LOG.info(f"RBD {ceph_location} will not be deleted because the image "
                 "is recorded through Brain")

    LOG.info(f"Deleting image {image_id} record from database")
    deleted_count = db.delete(IMAGE_COLLECTION, {"id": image_id})
    if deleted_count == 0:
        LOG.error(f"Failed to delete image {image_id} from database")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found"
        )

    LOG.info(f"Successfully deleted image {image_id} ({image_name})")