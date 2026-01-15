# Copyright (C) 2021 - 2025, Shanghai Yunsilicon Technology Co., Ltd.
# All rights reserved.

import re
from pydantic import BaseModel, Field, IPvAnyAddress, validator
from typing import Optional


class SystemDiskCreate(BaseModel):
    image_id: str = Field(..., description="Source image id")
    size_gb: int = Field(..., ge=1, description="Disk size in GB")
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
                "disk_id must match regex ^[A-Za-z0-9._-]+$ (no Chinese, no spaces)"
            )
        return v


class SystemUser(BaseModel):
    name: str = Field(..., description="System user name")
    password: str = Field(..., description="System user password")


class BareMetalCreate(BaseModel):
    system_disk: SystemDiskCreate
    system_user: SystemUser


class SystemDiskUpdate(BaseModel):
    description: Optional[str] = Field(None, description="Disk description")


class SystemDisk(BaseModel):
    id: str = Field(..., description="Unique identifier for the system disk")
    image_id: str = Field(..., description="Source image id")
    mv200_id: str = Field(..., description="Target MV200 server id")
    mv200_ip: str = Field(..., description="Target MV200 server IP address")
    size_gb: int = Field(..., ge=1, description="Disk size in GB")
    mon_host: IPvAnyAddress = Field(..., description="Ceph monitor host IP address")
    flatten: bool = Field(False,
                          description="Whether to execute flatten on the cloned system disk")
    rbd_path: str = Field(..., description="Target rbd in ceph cluster")
    blk_id: int = Field(..., description="Target blk uuid in soc")
    description: Optional[str] = Field(None, description="Disk description")
    creator: Optional[str] = Field(None, description="Creator")
    efi_uuid: Optional[str] = Field(None, description="UEFI Boot PartUUID")


class UploadToImage(BaseModel):
    dest_name: str = Field(None, description="Dest image name")
    dest_pool: str = Field(None, description="Dest pool name")
    description: Optional[str] = Field(None, description="Image description")


class RebuildAsImage(BaseModel):
    image_id: str = Field(..., description="Source image id")