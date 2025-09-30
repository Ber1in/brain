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

# Data models


@router.post("/images", response_model=image_schemas.Image, status_code=status.HTTP_201_CREATED)
async def create_image(image_data: image_schemas.ImageCreate):
    """
    Create a new image
    """
    try:
        # Check if name already exists
        existing_image = db.find(IMAGE_COLLECTION, {"name": image_data.name,
                                                    "mon_host": image_data.mon_host})
        if existing_image:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Image with this name already exists in ceph cluster {image_data.mon_host}"
            )

        # Check if ceph location already exists
        existing_location = db.find(IMAGE_COLLECTION, {"ceph_location": image_data.ceph_location,
                                                       "mon_host": image_data.mon_host})
        if existing_location:
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

        cephclient = get_cephclient(str(image_data.mon_host))
        try:
            snap_api = api.RbdSnapshotApi(cephclient)
            snap_api.api_block_image_image_spec_snap_post(
                image_spec=quote(image_data.ceph_location, safe=""),
                api_block_image_image_spec_snap_post_request={"snapshot_name": SNAP_NAME,
                                                              "mirrorImageSnapshot": False})
            snap_api.api_block_image_image_spec_snap_snapshot_name_put(
                image_spec=quote(image_data.ceph_location, safe=""),
                snapshot_name=SNAP_NAME,
                api_block_image_image_spec_snap_snapshot_name_put_request={"is_protected": True})
        except ApiException as e:
            LOG.error(f"Failed to create snapshot {SNAP_NAME} of the rbd "
                      f"{image_data.ceph_location}: {str(e)}")
            raise
        else:
            # Insert new image
            db.insert(IMAGE_COLLECTION, image_dict)

        # Return the created image information
        return image_dict

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        LOG.error(f"Failed to create image: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create image: {e}"
        )


@router.get("/images", response_model=List[image_schemas.Image])
async def get_all_images():
    """
    Get all images list
    """
    try:
        images = db.find(IMAGE_COLLECTION, {})
        # Return all images with their data
        return images
    except Exception as e:
        LOG.error(f"Failed to get images: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get images"
        )


@router.get("/images/{image_id}", response_model=image_schemas.Image)
async def get_image(image_id: str):
    """
    Get specific image by ID
    """
    try:
        image = db.find_one(IMAGE_COLLECTION, {"id": image_id})
        if not image:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Image not found"
            )

        return image
    except Exception as e:
        LOG.error(f"Failed to get image {image_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get image"
        )


@router.put("/images/{image_id}", response_model=image_schemas.Image)
async def update_image(image_id: str, update_data: image_schemas.ImageUpdate):
    """
    Update image information by ID
    """
    try:
        # Check if image exists
        existing_image = db.find_one(IMAGE_COLLECTION, {"id": image_id})
        if not existing_image:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Image not found"
            )

        # If updating name, check if name conflicts with other images
        if update_data.name and update_data.name != existing_image.get("name"):
            same_name_images = db.find(IMAGE_COLLECTION, {"name": update_data.name})
            if same_name_images:
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
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Another image with this ceph location already exists"
                )

        # Update image information (excluding ID field)
        update_dict = {k: v for k, v in update_data.dict(
            exclude_unset=True).items() if v is not None}
        if update_dict:
            updated_count = db.update(IMAGE_COLLECTION, {"id": image_id}, update_dict)
            if updated_count == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Image not found"
                )

        # Return updated image information
        updated_images = db.find(IMAGE_COLLECTION, {"id": image_id})
        updated_image = updated_images[0]
        return updated_image

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        LOG.error(f"Failed to update image {image_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update image"
        )


@router.delete("/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_image(image_id: str):
    """
    Delete image by ID
    """
    # Check if image exists
    existing_images = db.find_one(IMAGE_COLLECTION, {"id": image_id})
    if not existing_images:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found"
        )

    # Delete image
    cephclient = get_cephclient(existing_images["mon_host"])
    try:
        snap_api = api.RbdSnapshotApi(cephclient)
        snap_api.api_block_image_image_spec_snap_snapshot_name_put(
            image_spec=quote(existing_images["ceph_location"], safe=""),
            snapshot_name=SNAP_NAME,
            api_block_image_image_spec_snap_snapshot_name_put_request={"is_protected": False})
        snap_api.api_block_image_image_spec_snap_snapshot_name_delete(
            image_spec=quote(existing_images["ceph_location"], safe=""), 
            snapshot_name=SNAP_NAME)
    except ApiException as e:
        LOG.error(f"Failed to delete snapshot {SNAP_NAME} of the rbd "
                  f"{existing_images['ceph_location']}: {str(e)}")
        raise
    else:
        LOG.info(f"snapshot {SNAP_NAME} of the rbd {existing_images['ceph_location']} "
                 "has been deleted ")

    if existing_images.get("brain"):
        try:
            rbd_api = api.RbdApi(cephclient)
            rbd_api.api_block_image_image_spec_delete(
                image_spec=quote(existing_images["ceph_location"], safe=""))
            LOG.info(f"rbd {existing_images['ceph_location']} has been deleted "
                     "because the image was created through Brain")
        except ApiException as e:
            LOG.error(f"Failed to delete rbd {existing_images['ceph_location']}: {str(e)}")
            raise
    else:
        LOG.info(f"rbd {existing_images['ceph_location']} will not be deleted"
                 " because the image is recorded through Brain")

    deleted_count = db.delete(IMAGE_COLLECTION, {"id": image_id})
    if deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found"
        )
    LOG.info("Image deleted successfully.")