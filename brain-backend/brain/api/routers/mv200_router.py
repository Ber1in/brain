# Copyright (C) 2021 - 2025, Shanghai Yunsilicon Technology Co., Ltd.
# All rights reserved.

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
import logging
import uuid
import urllib3

from brain.json_db import JSONDocumentDB
from brain.auth import authenticate_user
from brain.api.schemas import mv200_schemas
from brain.clients.dpuagent import api as dpuagentApi
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

    # Generate unique ID and create server document
    server_id = str(uuid.uuid4())
    server_dict = {
        "id": server_id,
        **server_data.dict()
    }

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
    server = db.find_one(MV_SERVER_COLLECTION, {"id": server_id})
    if not server:
        LOG.warning(f"MV server {server_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="MV server not found"
        )

    try:
        setting_api = dpuagentApi.SettingsApi(get_dpuagentclient(server["ip_address"]))
        res = setting_api.get_clouddisk_enable_setting_dpu_agent_v1_settings_clouddisk_enable_get(
            _request_timeout=2)
        if res.code != 0:
            LOG.error(f"Failed to get clouddisk enable status for SOC "
                      f"{server['ip_address']}, message: {res.message}")
        else:
            server["clouddisk_enable"] = res.clouddisk_enable
            LOG.info(f"Clouddisk enable status for SOC {server['ip_address']}: "
                     f"{res.clouddisk_enable}")

    except (urllib3.exceptions.ConnectTimeoutError, urllib3.exceptions.MaxRetryError):
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Failed to connect to DPU agent at {server['ip_address']}"
        )

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
    update_dict = {k: v for k, v in update_data.dict(
        exclude_unset=True).items() if v is not None}

    if update_dict:
        LOG.info(f"Updating MV server {server_id} with fields: {list(update_dict.keys())}")

        # Handle clouddisk enable status update
        if update_data.clouddisk_enable != existing_server.get("clouddisk_enable"):
            soc_ip = existing_server["ip_address"]
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
