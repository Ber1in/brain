# Copyright (C) 2021 - 2025, Shanghai Yunsilicon Technology Co., Ltd.
# All rights reserved.
import re
from typing import Optional
from pydantic import BaseModel, Field, validator, IPvAnyAddress


class ImageCreate(BaseModel):
    name: str = Field(..., description="Image name")
    ceph_location: str = Field(..., description="Ceph location in format pool/rbd")
    mon_host: IPvAnyAddress = Field(..., description="Ceph monitor host IP address")
    min_size: int = Field(..., description="Minimum capacity when creating a system disk")
    description: Optional[str] = Field(None, description="Image description")

    @validator('ceph_location')
    def validate_ceph_location(cls, v):
        """Validate ceph location format: pool/rbd"""
        if not re.match(r'^[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+$', v):
            raise ValueError('Ceph location must be in format: pool/rbd')
        return v


class ImageUpdate(BaseModel):
    name: Optional[str] = Field(None, description="Image name")
    ceph_location: Optional[str] = Field(None, description="Ceph location in format pool/rbd")
    mon_host: Optional[IPvAnyAddress] = Field(None, description="Ceph monitor host IP address")
    min_size: int = Field(None, description="Minimum capacity when creating a system disk")
    description: Optional[str] = Field(None, description="Image description")

    @validator('ceph_location')
    def validate_ceph_location(cls, v):
        """Validate ceph location format: pool/rbd"""
        if v is not None and not re.match(r'^[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+$', v):
            raise ValueError('Ceph location must be in format: pool/rbd')
        return v


class Image(BaseModel):
    id: str = Field(..., description="Unique identifier for the image")
    name: str = Field(..., description="Image name")
    ceph_location: str = Field(..., description="Ceph location in format pool/rbd")
    min_size: int = Field(..., description="Minimum capacity when creating a system disk")
    mon_host: IPvAnyAddress = Field(..., description="Ceph monitor host IP address")
    description: Optional[str] = Field(None, description="Image description")
