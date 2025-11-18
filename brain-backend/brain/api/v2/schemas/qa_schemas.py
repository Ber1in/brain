# Copyright (C) 2021 - 2025, Shanghai Yunsilicon Technology Co., Ltd.
# All rights reserved.

from typing import List
from pydantic import BaseModel, root_validator


class CheckoutRequest(BaseModel):
    branch: str = None
    tag: str = None

    @root_validator
    def check_exclusive(cls, values):
        branch, tag = values.get("branch"), values.get("tag")
        if branch and tag:
            raise ValueError("Cannot provide both branch and tag at the same time")
        if not branch and not tag:
            raise ValueError("Either branch or tag must be provided")
        return values


class BranchAndTagResponse(BaseModel):
    branchs: List[str] = None
    tags: List[str] = None
    current: str
    latest_commit: str


class DirNeedCollectRequest(BaseModel):
    dirs: List[str]


class CasesResponse(BaseModel):
    cases: List[str] = None


class ExecuteNicInfo(BaseModel):
    iface: str
    ipv4: str = None
    ipv6: str = None
    bdf: str

    @root_validator
    def check_ip(cls, values):
        ipv4, ipv6 = values.get("ipv4"), values.get("ipv6")
        if not ipv4 and not ipv6:
            raise ValueError("Either ipv4 or ipv6 must be provided.")
        return values


class Server(BaseModel):
    device_id: str
    nics: List[ExecuteNicInfo] = None


class ExecuteRequest(BaseModel):
    cases: List[str] = None
    servers: List[Server] = None


class ExecuteResponse(BaseModel):
    url: str = None
    time: str = None
    current: str = None
    commit: str = None


class CaseCombinationsResponse(BaseModel):
    id: str
    name: str
    created_at: str
    cases: List[str] = None


class CaseCombinationsRequest(BaseModel):
    name: str
    cases: List[str] = None