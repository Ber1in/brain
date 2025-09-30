# Copyright (C) 2021 - 2025, Shanghai Yunsilicon Technology Co., Ltd.
# All rights reserved.

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
import logging
import uuid

from brain.json_db import JSONDocumentDB
from brain.auth import authenticate_user
from brain.api.schemas import bare_metal_schemas

router = APIRouter(dependencies=[Depends(authenticate_user)])
LOG = logging.getLogger(__name__)
db = JSONDocumentDB()

# Collection name
BARE_METAL_SERVER_COLLECTION = "bare_metals"


@router.post("/bare-metals", response_model=bare_metal_schemas.BareMetalServer,
             status_code=status.HTTP_201_CREATED)
async def create_bare_metal_server(server_data: bare_metal_schemas.BareMetalServerCreate):
    """
    Create a new bare metal
    """
    try:
        # Check if name already exists
        existing_server = db.find(BARE_METAL_SERVER_COLLECTION, {"name": server_data.name})
        if existing_server:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Server with this name already exists"
            )

        # Check if IP address already exists
        existing_ip = db.find(BARE_METAL_SERVER_COLLECTION, {"host_ip": server_data.host_ip})
        if existing_ip:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Server with this IP address already exists"
            )

        # Generate unique ID and create server document
        server_id = str(uuid.uuid4())
        server_dict = {
            "id": server_id,
            **server_data.dict()
        }

        # Insert new server
        db.insert(BARE_METAL_SERVER_COLLECTION, server_dict)

        # Return the created server information
        return server_dict

    except Exception as e:
        LOG.error(f"Failed to create bare metal: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create bare metal: {e}"
        )


@router.get("/bare-metals", response_model=List[bare_metal_schemas.BareMetalServer])
async def get_all_bare_metals():
    """
    Get all bare metals list
    """
    try:
        servers = db.find(BARE_METAL_SERVER_COLLECTION, {})
        # Filter out any internal fields and return only the data
        return servers
    except Exception as e:
        LOG.error(f"Failed to get bare metals: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get bare metals"
        )


@router.get("/bare-metals/{server_id}", response_model=bare_metal_schemas.BareMetalServer)
async def get_bare_metal_server(server_id: str):
    """
    Get specific bare metal by ID
    """
    try:
        server = db.find_one(BARE_METAL_SERVER_COLLECTION, {"id": server_id})
        if not server:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="bare metal not found"
            )

        return server
    except Exception as e:
        LOG.error(f"Failed to get bare metal {server_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get bare metal"
        )


@router.put("/bare-metals/{server_id}", response_model=bare_metal_schemas.BareMetalServer)
async def update_bare_metal_server(
        server_id: str, update_data: bare_metal_schemas.BareMetalServerUpdate):
    """
    Update bare metal information by ID
    """
    try:
        # Check if server exists
        existing_server = db.find_one(BARE_METAL_SERVER_COLLECTION, {"id": server_id})
        if not existing_server:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="bare metal not found"
            )

        # If updating name, check if name conflicts with other servers
        if update_data.name and update_data.name != existing_server.get("name"):
            same_name_servers = db.find(BARE_METAL_SERVER_COLLECTION, {"name": update_data.name})
            if same_name_servers:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Another server with this name already exists"
                )

        # If updating IP address, check if IP conflicts with other servers
        if update_data.host_ip and update_data.host_ip != existing_server.get("host_ip"):
            same_ip_servers = db.find(BARE_METAL_SERVER_COLLECTION,
                                      {"host_ip": update_data.host_ip})
            if same_ip_servers:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Another server with this IP address already exists"
                )

        # Update server information (excluding ID field)
        update_dict = {k: v for k, v in update_data.dict(
            exclude_unset=True).items() if v is not None}
        if update_dict:
            updated_count = db.update(BARE_METAL_SERVER_COLLECTION, {"id": server_id}, update_dict)
            if updated_count == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="bare metal not found"
                )

        # Return updated server information
        updated_server = db.find_one(BARE_METAL_SERVER_COLLECTION, {"id": server_id})
        return updated_server

    except HTTPException:
        raise
    except Exception as e:
        LOG.error(f"Failed to update bare metal {server_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update bare metal"
        )


@router.delete("/bare-metals/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bare_metal_server(server_id: str):
    """
    Delete bare metal by ID
    """
    try:
        # Check if server exists
        existing_servers = db.find(BARE_METAL_SERVER_COLLECTION, {"id": server_id})
        if not existing_servers:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="bare metal not found"
            )

        # Delete server
        deleted_count = db.delete(BARE_METAL_SERVER_COLLECTION, {"id": server_id})
        if deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="bare metal not found"
            )

    except HTTPException:
        raise
    except Exception as e:
        LOG.error(f"Failed to delete bare metal {server_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete bare metal"
        )