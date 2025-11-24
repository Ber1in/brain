# Copyright (C) 2021 - 2025, Shanghai Yunsilicon Technology Co., Ltd.
# All rights reserved.

import re
from pydantic import BaseModel, Field
from typing import Dict, Optional
from pydantic import validator


class BareMetalServerCreate(BaseModel):
    name: str
    host_ip: str
    mac: str
    gateway: str
    description: Optional[str] = None

    @validator("mac")
    def validate_mac(cls, value: str):

        regex = re.compile(r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$")
        value = value.replace("-", ":").lower()
        if not regex.match(value):
            raise ValueError(
                f"Invalid MAC address format: '{value}'. Must be in the form of 'XX:XX:XX:XX:XX:XX'"
                " or 'XX-XX-XX-XX-XX-XX' (e.g. '00:1A:2B:3C:4D:5E')"
            )
        # Reject all-zeros or all-FF (case-insensitive)
        if value in ("00:00:00:00:00:00", "ff:ff:ff:ff:ff:ff"):
            raise ValueError(f"Disallowed MAC address: '{value}' (cannot be all 0s or all Fs)")
        return value


class BareMetalServerUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    host_ip: Optional[str] = None
    mac: Optional[str] = None
    gateway: Optional[str] = None
    os_user: Optional[str] = None
    os_password: Optional[str] = None 


class BareMetalServer(BaseModel):
    id: str = Field(..., description="Unique identifier for the BareMetal server")
    name: str
    description: Optional[str] = None
    host_ip: Optional[str] = None
    mac: Optional[str] = None
    gateway: Optional[str] = None  
    os_user: Optional[str] = None 
    os_password: Optional[str] = None


class BootEntriesResponse(BaseModel):
    entries: Dict[str, str]
    current: str
    next: str = Field(None)
    default: str = Field(None)


class ServerCredentials(BaseModel):
    user: str
    pwd: str