# Copyright (C) 2021 - 2025, Shanghai Yunsilicon Technology Co., Ltd.
# All rights reserved.

from fastapi import APIRouter, Depends, HTTPException, status
import logging
from typing import List
import uuid
import random

from brain.auth import authenticate_user
from brain.json_db import JSONDocumentDB
from brain.api.schemas import network_schemas
from brain.clients.dpuagent import api
from brain.utils.get_client import get_dpuagentclient

router = APIRouter(dependencies=[Depends(authenticate_user)])
LOG = logging.getLogger(__name__)
db = JSONDocumentDB()

NETWORK_COLLECTION = "networks"
MV_SERVER_COLLECTION = "mv_servers"


@router.post("/networks", response_model=network_schemas.InterfaceInfo)
async def create_interface(data: network_schemas.InterfaceCreate):
    """Create a new network interface"""
    interface_id = str(uuid.uuid4())
    LOG.info(f"Creating interface {interface_id} on SoC {data.mv200_id} with IP {data.ip}")

    server = db.find_one(MV_SERVER_COLLECTION, {"id": data.mv200_id})
    if not server:
        LOG.warning(f"MV server {data.mv200_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="MV server not found"
        )

    interface_data = data.dict()
    if not interface_data.get("mac"):
        interface_data["mac"] = "02:00:%02x:%02x:%02x:%02x" % (
            random.randint(0x00, 0x7f),
            random.randint(0x00, 0xff),
            random.randint(0x00, 0xff),
            random.randint(0x00, 0xff),
        )
        LOG.info(f"Generated MAC {interface_data['mac']} for interface {interface_id}")

    dpuagentclient = get_dpuagentclient(server["ip_address"])
    xscapi = api.XscnetApi(dpuagentclient)
    try:
        res = xscapi.create_xscnet_dpu_agent_v1_xscnet_add_post(
            {
                "vq_count": 2,
                "vq_size": 512,
                "mac": interface_data["mac"],
                "mtu": data.mtu,
            }
        )
        if res.code != 0:
            LOG.error(
                f"Failed to create XSC network for interface {interface_id} "
                f"on SoC {server['ip_address']}: {res.message}"
            )
            raise HTTPException(status_code=500, detail=res.message)
        interface_data["xsc_id"] = res.uuid
        LOG.info(
            f"XSC network created for interface {interface_id}, uuid={res.uuid}"
        )
    except Exception as e:
        LOG.error(f"Exception creating XSC network for {interface_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    ovsapi = api.OvsflowApi(dpuagentclient)
    try:
        params = {
            "uuid": interface_data["xsc_id"],
            "vlan": data.vlan_tag,
            "ip": str(data.ip),
            "gw_ip": data.gateway,
            "src_mac": interface_data["mac"],
            "dhcp_server": data.gateway,
        }
        if data.dns:
            params["dns"] = data.dns
        res = ovsapi.add_ovsflow_dpu_agent_v1_ovsflow_add_post(params)
        if res.code != 0:
            LOG.error(
                f"Failed to add OVS flow for interface {interface_id} "
                f"on SoC {server['ip_address']}: {res.message}"
            )
            raise HTTPException(status_code=500, detail=res.message)
        LOG.info(f"OVS flow added for interface {interface_id} successfully")
    except Exception as e:
        LOG.error(f"Exception adding OVS flow for {interface_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    interface_data["id"] = interface_id
    db.insert(NETWORK_COLLECTION, interface_data)
    LOG.info(f"Interface {interface_id} inserted into database")
    return interface_data


@router.delete("/networks", status_code=status.HTTP_204_NO_CONTENT)
async def delete_interface(data: network_schemas.InterfaceDelete):
    """Delete an existing network interface"""
    LOG.info(f"Deleting interface {data.id} on SoC {data.mv200_id}")

    interface = db.find_one(NETWORK_COLLECTION, {"id": data.id})
    if not interface:
        LOG.warning(f"Interface {data.id} not found in database")
        raise HTTPException(status_code=404, detail="Interface not found")

    server = db.find_one(MV_SERVER_COLLECTION, {"id": data.mv200_id})
    if not server:
        LOG.warning(f"MV server {data.mv200_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="MV server not found"
        )

    dpuagentclient = get_dpuagentclient(server['ip_address'])
    try:
        res = api.XscnetApi(dpuagentclient).delete_xscnet_dpu_agent_v1_xscnet_del_post(
            {"uuid": interface["xsc_id"]}
        )
        if res.code != 0:
            LOG.error(
                f"Failed to delete XSC network for interface {data.id} "
                f"on SoC {server['ip_address']}: {res.message}"
            )
            raise HTTPException(status_code=500, detail=res.message)
        LOG.info(f"XSC network for interface {data.id} deleted successfully")
    except Exception as e:
        LOG.error(f"Exception deleting XSC network for {data.id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    db.delete(NETWORK_COLLECTION, {"id": data.id})
    LOG.info(f"Interface {data.id} deleted successfully")
    return


@router.put("/networks", response_model=network_schemas.InterfaceInfo)
async def update_interface_description(data: network_schemas.InterfaceUpdate):
    """Update description of an existing interface"""
    LOG.info(f"Updating description for interface {data.id}: {data.description}")
    updated = db.update(
        NETWORK_COLLECTION, {"id": data.id}, {"description": data.description}
    )
    if not updated:
        LOG.warning(f"Interface {data.id} not found for update")
        raise HTTPException(status_code=404, detail="Interface not found")

    interface = db.find_one(NETWORK_COLLECTION, {"id": data.id})
    LOG.info(f"Interface {data.id} description updated successfully")
    return interface


@router.get("/networks", response_model=List[network_schemas.InterfaceInfo])
async def list_interfaces():
    """List all network interfaces"""
    LOG.info("Listing all network interfaces")
    interfaces = db.find(NETWORK_COLLECTION)
    LOG.info(f"Found {len(interfaces)} interfaces")
    return interfaces


@router.get("/networks/{interface_id}", response_model=network_schemas.InterfaceInfo)
async def get_interface(interface_id: str):
    """Get a single network interface by its ID"""
    LOG.info(f"Fetching interface {interface_id}")
    interface = db.find_one(NETWORK_COLLECTION, {"id": interface_id})
    if not interface:
        LOG.warning(f"Interface {interface_id} not found")
        raise HTTPException(status_code=404, detail="Interface not found")

    server = db.find_one(MV_SERVER_COLLECTION, {"id": interface["mv200_id"]})
    if not server:
        LOG.warning(f"MV server {interface['mv200_id']} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="MV server not found"
        )
    try:
        dpuagentclient = get_dpuagentclient(server["ip_address"])
        res = api.RdmaApi(dpuagentclient).list_nics_info_dpu_agent_v1_rdma_list_nics_get()
        if res.code != 0:
            LOG.error()
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=f"Failed to connect to DPU agent at {server['ip_address']}"
            )
        for nic in res.nics_info:
            if (nic.ip_addr == interface["ip"].split("/")[0] and
                    nic.mac.replace("-", ":") == interface['mac'].lower()):
                interface["ifname"] = nic.ifname
    except Exception as e:
        LOG.warning(f"Failed to obtain the network port name, error: {e}")

    LOG.info(f"Interface {interface_id} fetched successfully")
    return interface

