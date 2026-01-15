# Copyright (C) 2021 - 2025, Shanghai Yunsilicon Technology Co., Ltd.
# All rights reserved.

from pydantic import BaseModel, Field,Extra
from typing import List, Optional
from ipaddress import IPv4Address

from brain.api.v1.schemas.network_schemas import IPWithNetmask, Mac


class MVServerCreate(BaseModel):
    name: str
    ip_address: str
    description: Optional[str] = None


class MVServerUpdate(BaseModel):
    name: Optional[str] = None
    ip_address: Optional[str] = None
    description: Optional[str] = None
    auto: bool = False
    clouddisk_enable: bool
    recovery_mode: Optional[str] = None


class MCRVersionInfo(BaseModel):
    driver: str
    firmware: str
    dpuagent: str


class MVServer(BaseModel):
    id: str = Field(..., description="Unique identifier for the MV server")
    name: str
    ip_address: str
    description: Optional[str] = None
    mac: str = None
    sn: str = None
    gateway: IPv4Address = None
    nic_sn: str = None
    versions: MCRVersionInfo = None
    clouddisk_enable: bool = Field(..., 
                                   description=("The host allows the use of system cloud disk"
                                                " (waiting for dpu ready when the host starts)"))
    recovery_mode: Optional[str] = Field(None,
                                         description="The recovery mode of aidpu, the "
                                                     "value is one of auto and manual")

    task_id: str = None


class InterfaceCreate(BaseModel):
    pxe: bool = Field(False)
    uuid: int = None
    vq_count: int = Field(2, description="Optional field, vq count", example=2)
    vq_size: int = Field(512, description="Optional field, vq size", example=512)
    mtu: int = Field(1500, description="Optional field, MTU size", example=1500)
    mac: Optional[Mac] = Field(None, description="MAC address of the interface (optional)")


class XscnetInfoResponse(BaseModel):
    uuid: int
    mtu: int
    mac: Mac
    vlan: Optional[int] = None
    ip: Optional[IPWithNetmask] = None
    gateway: Optional[str] = None
    dhcp_server: Optional[str] = None
    ifname: Optional[str] = None
    dns: List[str] = []


class OvsflowRequest(BaseModel):
    mac: str
    ip: IPWithNetmask = Field(..., description="IP address with CIDR mask, e.g., 192.168.1.10/24")
    vlan_tag: int = Field(..., description="VLAN tag for the interface")
    gateway: str = Field(None, description="Gateway address for the interface")
    dns: Optional[List[str]] = Field(None, description="List of DNS server addresses (optional)")
    dhcp_server: str = Field(None, description="Dhcp server address for the interface")




class BdevInfo(BaseModel):
    readonly: bool = Field(...,
                           description="Indicates if the block device is read-only", example=False)
    bdev: str = Field(..., description="Name of the block device")

    class Config:
        extra = Extra.allow


class BackendSpecific(BaseModel):
    block: BdevInfo


class ControllerInfo(BaseModel):
    ctrlr: str = Field(..., description="Name of the virtual block controller")
    cpumask: str = Field(..., description="CPU core mask assigned to the controller", example="0x8")
    uuid: int = Field(..., description="Unique identifier for the controller")
    vq_count: int = Field(..., description="Number of virtual queues", example=2)
    vq_size: int = Field(..., description="Size of each virtual queue", example=512)
    backend_specific: BackendSpecific
