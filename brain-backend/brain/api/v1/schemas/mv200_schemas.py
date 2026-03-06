# Copyright (C) 2021 - 2025, Shanghai Yunsilicon Technology Co., Ltd.
# All rights reserved.

import re
from pydantic import BaseModel, Field, validator, ConstrainedStr
from pydantic.validators import str_validator
from ipaddress import ip_interface
from typing import List, Optional
from ipaddress import IPv4Address


class IPWithNetmask(str):
    @classmethod
    def __get_validators__(cls):
        yield str_validator
        yield cls.validate

    @classmethod
    def validate(cls, value: str) -> str:
        # Check that both IP and netmask are provided
        values = value.split("/")
        if len(values) != 2:
            raise ValueError("Missing netmask. Format must be IP/MASK (e.g., 192.168.1.10/24)")

        # Ensure that the mask is given as number of bits, not a specific mask
        try:
            int(values[1])
        except ValueError:
            raise ValueError("Expects the number of mask bits, not the specific mask")

        # Validate the IP address format using ip_interface
        iface = ip_interface(value)
        # Ensure it is a host IP, not the network address
        if iface.ip == iface.network.network_address:
            raise ValueError("IP must be a host address, not the network address")

        return value

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(
            example="127.0.0.1/24",
            format="ip-netmask",
            description="IP/Netmask (support IPv4/IPv6)"
        )


class Mac(ConstrainedStr):
    regex = re.compile(r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$")

    @classmethod
    def validate(cls, value: str):
        value = value.replace("-", ":").lower()
        if not cls.regex.match(value):
            raise ValueError(
                f"Invalid MAC address format: '{value}'. Must be in the form of 'XX:XX:XX:XX:XX:XX'"
                " or 'XX-XX-XX-XX-XX-XX' (e.g. '00:1A:2B:3C:4D:5E')"
            )
        # Reject all-zeros or all-FF (case-insensitive)
        if value in ("00:00:00:00:00:00", "ff:ff:ff:ff:ff:ff"):
            raise ValueError(f"Disallowed MAC address: '{value}' (cannot be all 0s or all Fs)")
        return value


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
    sub_product_id: Optional[int] = None
    switch_emu_enable: Optional[int] = None
    vm_emu_enable: Optional[int] = None

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
    gws: Optional[List[str]] = Field(None)


class BackendSpecific(BaseModel):
    block: BdevInfo


class ControllerInfo(BaseModel):
    ctrlr: str = Field(..., description="Name of the virtual block controller")
    cpumask: str = Field(..., description="CPU core mask assigned to the controller", example="0x8")
    uuid: int = Field(..., description="Unique identifier for the controller")
    vq_count: int = Field(..., description="Number of virtual queues", example=2)
    vq_size: int = Field(..., description="Size of each virtual queue", example=512)
    backend_specific: BackendSpecific


class SystemDiskCreate(BaseModel):
    image_id: str = Field(..., description="Source image id")
    size_gb: int = Field(..., ge=1, description="Disk size in GB")
    mon_hosts: List[str] = Field(..., description="ceph mon address list")
    vq_count: int = Field(2)
    vq_size: int = Field(512)
    disk_id: Optional[str] = Field(None, description="rbd image name (ASCII only)")
    pool: Optional[str] = Field(
        "compute", description="ceph osd pool for new rbd (default: compute)")
    flatten: bool = Field(False, 
                          description="Whether to execute flatten on the cloned system disk")

    @validator("disk_id")
    def validate_disk_id(cls, v):
        disk_id_pattren = r"^[A-Za-z0-9._-]+$"
        disk_id_re = re.compile(disk_id_pattren)

        if v is None:
            return v

        if not disk_id_re.match(v):
            raise ValueError(
                f"disk_id must match regex ^[A-Za-z0-9._-]+$ (no Chinese, no spaces), not {v}"
            )
        return v


class SystemUser(BaseModel):
    name: str = Field(..., description="System user name")
    password: str = Field(..., description="System user password")


class CloudDiskCreateRequest(BaseModel):
    system_disk: SystemDiskCreate
    system_user: SystemUser


class SystemDiskCreateResponse(BaseModel):
    efi_status: int = None
    cloudinit_status: int = None


class SystemDiskDeleteRequest(BaseModel):
    uuid: int
    rbd_path: str
    mon_hosts: str
    bare_id: str
    last_disk: bool
