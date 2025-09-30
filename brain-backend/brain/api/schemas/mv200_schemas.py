# Copyright (C) 2021 - 2025, Shanghai Yunsilicon Technology Co., Ltd.
# All rights reserved.

from pydantic import BaseModel, Field
from typing import Optional


class MVServerCreate(BaseModel):
    name: str
    ip_address: str
    description: Optional[str] = None
    bare_id: str = None


class MVServerUpdate(BaseModel):
    name: Optional[str] = None
    ip_address: Optional[str] = None
    description: Optional[str] = None
    bare_id: Optional[str] = None
    clouddisk_enable: bool


class MVServer(BaseModel):
    id: str = Field(..., description="Unique identifier for the MV server")
    name: str
    ip_address: str
    description: Optional[str] = None
    bare_id: Optional[str] = None
    clouddisk_enable: bool = Field(..., 
                                   description=("The host allows the use of system cloud disk"
                                                " (waiting for dpu ready when the host starts)"))