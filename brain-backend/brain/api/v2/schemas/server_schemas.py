# Copyright (C) 2021 - 2025, Shanghai Yunsilicon Technology Co., Ltd.
# All rights reserved.

from pydantic import BaseModel, Field
from ipaddress import IPv4Address
from typing import List, Optional, Union, Dict


class BMC(BaseModel):
    ip: IPv4Address = None
    hostname: str


class DeviceRequest(BaseModel):
    sn: str = None
    ip: IPv4Address
    username: str
    password: str


class DeviceResponse(BaseModel):
    sn: str = None
    ip: str
    username: str
    mac: str = None
    gateway: str = None
    vendor: str = None
    product: str = None
    arch: str = None
    cpu_vendor: str = None
    cpu_mode: str = None


class NicInfo(BaseModel):
    mac: str = None
    bdf: str = None
    iface: str = None
    switch: str = None
    port: str = None
    ipv4: List[str] = []
    ipv6: List[str] = []


class NicBase(BaseModel):
    type: str
    nic_info: List[NicInfo] = None
    sn: str
    pcie_width: str = None


class AIDPU_Nic(NicBase):
    soc_ip: IPv4Address
    aidpu_sn: str = None
    firmware_version: str = None
    management_ip: str = None


class BootEntriesResponse(BaseModel):
    entries: Dict[str, str]
    current: str
    next: str = Field(None)
    default: str = Field(None)


class ServerRequest(BaseModel):
    bmc: BMC = Field(...)
    device: DeviceRequest = Field(...)
    nics: List[Union[NicBase, AIDPU_Nic]] = None
    tags: List[str] = []
    notes: str = None


class ServerResponse(BaseModel):
    bmc: BMC = Field(...)
    device: DeviceResponse = Field(...)
    nics: List[Union[NicBase, AIDPU_Nic]] = None
    tags: List[str] = []
    notes: str = None


class ServerDetailResponse(ServerResponse):
    user: str = None
    time: str = None
    created_at: str = None
    updated_at: str = None
    id: str = None
    recipients: List[str] = []
    task_id: str = None
    lock: int = None


class ServerUpdateRequest(BaseModel):
    auto: bool = False
    device: Optional[DeviceRequest] = None
    bmc: Optional[BMC] = None
    nics: List[Union[NicBase, AIDPU_Nic]] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = None
    time: Optional[str] = None
    focus: bool = False


class LockRequest(BaseModel):
    lock: int


class ServerOccupyRequest(BaseModel):
    time: Optional[str] = None


class HeartBeatResponse(BaseModel):
    user: Optional[str] = None
    time: Optional[str] = None
    next_checkin: int


class OsInfoResponse(BaseModel):
    system_version: Optional[str] = None
    kernel_version: Optional[str] = None
