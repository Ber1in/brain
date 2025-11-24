# Copyright (C) 2021 - 2025, Shanghai Yunsilicon Technology Co., Ltd.
# All rights reserved.

from pydantic import BaseModel, Field
from typing import Optional
from ipaddress import IPv4Address


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