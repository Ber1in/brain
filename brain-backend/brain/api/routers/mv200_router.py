# Copyright (C) 2021 - 2025, Shanghai Yunsilicon Technology Co., Ltd.
# All rights reserved.

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
import logging
import uuid

from brain.json_db import JSONDocumentDB
from brain.auth import authenticate_user
from brain.api.schemas import mv200_schemas
from brain.clients.dpuagent import SettingsApi
from brain.utils.get_client import get_dpuagentclient

router = APIRouter(dependencies=[Depends(authenticate_user)])
LOG = logging.getLogger(__name__)
db = JSONDocumentDB()

# Collection name
MV_SERVER_COLLECTION = "mv_servers"


@router.post("/mv-servers", response_model=mv200_schemas.MVServer,
             status_code=status.HTTP_201_CREATED)
async def create_mv_server(server_data: mv200_schemas.MVServerCreate):
    """
    Create a new MV server
    """
    try:
        # Check if name already exists
        existing_server = db.find(MV_SERVER_COLLECTION, {"name": server_data.name})
        if existing_server:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Server with this name already exists"
            )

        # Check if IP address already exists
        existing_ip = db.find(MV_SERVER_COLLECTION, {"ip_address": server_data.ip_address})
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

        setting_api = SettingsApi(get_dpuagentclient(server_data.ip_address))
        res = setting_api.get_clouddisk_enable_setting_dpu_agent_v1_settings_clouddisk_enable_get()
        server_dict["clouddisk_enable"] = False
        if res.code != 0:
            LOG.error(F"Failed to get clouddisk enable status for SOC {server_data.ip_address}"
                      f", message: {res.message}")
        else:
            server_dict["clouddisk_enable"] = res.clouddisk_enable

        # Insert new server
        db.insert(MV_SERVER_COLLECTION, server_dict)

        # Return the created server information
        return server_dict

    except Exception as e:
        LOG.error(f"Failed to create MV server: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create MV server: {e}"
        )


@router.get("/mv-servers", response_model=List[mv200_schemas.MVServer])
async def get_all_mv_servers():
    """
    Get all MV servers list
    """
    try:
        servers = db.find(MV_SERVER_COLLECTION, {})
        # Filter out any internal fields and return only the data
        return servers
    except Exception as e:
        LOG.error(f"Failed to get MV servers: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get MV servers"
        )


@router.get("/mv-servers/{server_id}", response_model=mv200_schemas.MVServer)
async def get_mv_server(server_id: str):
    """
    Get specific MV server by ID
    """
    try:
        server = db.find_one(MV_SERVER_COLLECTION, {"id": server_id})
        if not server:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="MV server not found"
            )

        return server
    except Exception as e:
        LOG.error(f"Failed to get MV server {server_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get MV server"
        )


@router.put("/mv-servers/{server_id}", response_model=mv200_schemas.MVServer)
async def update_mv_server(server_id: str, update_data: mv200_schemas.MVServerUpdate):
    """
    Update MV server information by ID
    """
    try:
        # Check if server exists
        existing_server = db.find_one(MV_SERVER_COLLECTION, {"id": server_id})
        if not existing_server:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="MV server not found"
            )

        # If updating name, check if name conflicts with other servers
        if update_data.name and update_data.name != existing_server.get("name"):
            same_name_servers = db.find(MV_SERVER_COLLECTION, {"name": update_data.name})
            if same_name_servers:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Another server with this name already exists"
                )

        # If updating IP address, check if IP conflicts with other servers
        if update_data.ip_address and update_data.ip_address != existing_server.get("ip_address"):
            same_ip_servers = db.find(MV_SERVER_COLLECTION, {"ip_address": update_data.ip_address})
            if same_ip_servers:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Another server with this IP address already exists"
                )

        # Update server information (excluding ID field)
        update_dict = {k: v for k, v in update_data.dict(
            exclude_unset=True).items() if v is not None}
        if update_dict:
            if update_data.clouddisk_enable != existing_server.get("clouddisk_enable"):
                setting_api = SettingsApi(get_dpuagentclient(existing_server["ip_address"]))
                res = setting_api.enable_pxe_dpu_agent_v1_settings_clouddisk_enable_put(
                    {"clouddisk_enable": update_data.clouddisk_enable})
                if res.code != 0:
                    LOG.error("Failed to update clouddisk enable status for SOC "
                              f"{existing_server['ip_address']}, message: {res.message}")
                    update_dict["clouddisk_enable"] = existing_server["clouddisk_enable"]
            updated_count = db.update(MV_SERVER_COLLECTION, {"id": server_id}, update_dict)
            if updated_count == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="MV server not found"
                )

        # Return updated server information
        updated_server = db.find_one(MV_SERVER_COLLECTION, {"id": server_id})
        return updated_server

    except HTTPException:
        raise
    except Exception as e:
        LOG.error(f"Failed to update MV server {server_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update MV server"
        )


@router.delete("/mv-servers/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mv_server(server_id: str):
    """
    Delete MV server by ID
    """
    try:
        # Check if server exists
        existing_servers = db.find(MV_SERVER_COLLECTION, {"id": server_id})
        if not existing_servers:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="MV server not found"
            )

        # Delete server
        deleted_count = db.delete(MV_SERVER_COLLECTION, {"id": server_id})
        if deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="MV server not found"
            )

    except HTTPException:
        raise
    except Exception as e:
        LOG.error(f"Failed to delete MV server {server_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete MV server"
        )