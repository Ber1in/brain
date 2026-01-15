# Copyright (C) 2021 - 2025, Shanghai Yunsilicon Technology Co., Ltd.
# All rights reserved.

import asyncio
import copy
import random
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
import logging
import uuid
import urllib3
from brain.api.v2.schemas import common_schemas

from brain.json_db import SQLiteDocumentDB
from brain.auth import authenticate_user
from brain.api.v1.schemas import mv200_schemas
from brain.clients.dpuagent import api as dpuagentApi
from brain.utils.get_client import get_dpuagentclient
from brain.utils.ssh_client import ssh_execute_async
from brain.utils import common_utils
from brain import exceptions

router = APIRouter(dependencies=[Depends(authenticate_user)])
LOG = logging.getLogger(__name__)
db = SQLiteDocumentDB()

# Collection name
MV_SERVER_COLLECTION = "mv_servers"
MV200_OS_USER = "root"
MV200_OS_PASSWORD = "yunsilicon"


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

    except (urllib3.exceptions.ConnectTimeoutError, urllib3.exceptions.MaxRetryError):
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Failed to connect to DPU agent at {server['ip_address']}"
        )
    # except dpuagentExp.NotFoundException:
    #     LOG.warning(f"DPU agent at {server['ip_address']} does not support "
    #                 "recovery mode query API (possibly old version)")

    db.update(MV_SERVER_COLLECTION, {"id": server_id}, server_original)
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
        if nic.ip_addr == "0.0.0.0":
            continue

        mac = nic.mac.lower().replace("-", ":")
        ip = nic.ip_addr.strip()

        nic_index[(mac, ip)] = nic.ifname

    for xsc in xscs:
        if not xsc.get("mac") or not xsc.get("ip"):
            continue

        xsc_mac = xsc["mac"].lower()
        xsc_ip = xsc["ip"].split("/", 1)[0]

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
        res = xscapi.create_xscnet_dpu_agent_v1_xscnet_add_post(
            {
                "pxe": data.pxe,
                "vq_count": data.vq_count,
                "vq_size": data.vq_size,
                "mac": iface_data["mac"],
                "mtu": data.mtu,
            }
        )
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


@router.post("/mv-servers/{server_id}/xsc/{uuid}/flowtables", status_code=status.HTTP_204_NO_CONTENT)
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


@router.delete("/mv-servers/{server_id}/xsc/{uuid}/flowtables", status_code=status.HTTP_204_NO_CONTENT)
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

@router.get("/mv-servers/{server_id}/systemdisks", response_model=List[mv200_schemas.ControllerInfo])
async def get_systemdisks(server_id: str, uuid: Optional[int] = Query(None, ge=1, le=100)):
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
            res = dpuagentApi.VblkApi(
                dpuagentclient).list_vblk_controllers_dpu_agent_v1_vblk_list_get()
        else:
            res = dpuagentApi.VblkApi(
                dpuagentclient).list_vblk_controllers_dpu_agent_v1_vblk_list_get(uuid)

        if res.code != 0:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=f"Failed to list xscnet at {mv200_ip}"
            )
    except Exception as e:
        LOG.warning(f"Failed to obtain the network port name, error: {e}")
        return []

    LOG.info(f"Interface for {mv200_ip} fetched successfully")
    return res.vblks