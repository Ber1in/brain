# Copyright (C) 2021 - 2025, Shanghai Yunsilicon Technology Co., Ltd.
# All rights reserved.

from pydantic import BaseModel, validator, root_validator
from typing import Any, Dict, List, Optional


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
    iface: str = None
    bdf: str = None
    type: str
    mac: str = None
    soc: str = None
    switch: str = None
    port: str = None

    @root_validator
    def validate_required_fields(cls, values):
        raw_type = values.get("type") or ""
        t_norm = (
            raw_type.lower()
                    .replace("-", "")
                    .replace(" ", "")
        )

        mv200_aliases = (
            "mv200",
            "metavisor200",
        )

        is_mv200 = any(token in t_norm for token in mv200_aliases)

        if is_mv200:
            if not values.get("soc"):
                raise ValueError("Field 'soc' is required when type is MV200")

        else:
            # When type is NOT MV200 → iface and bdf required
            if not values.get("iface"):
                raise ValueError("Field 'iface' is required when type is not MV200")
            if not values.get("mac"):
                raise ValueError("Field 'mac' is required when type is not MV200")
            if not values.get("bdf"):
                raise ValueError("Field 'bdf' is required when type is not MV200")

        return values


class Server(BaseModel):
    device_id: str
    nics: List[ExecuteNicInfo] = []


class ExecuteRequest(BaseModel):
    cases: List[str] = None
    servers: List[Server] = None


class ExecuteResponse(BaseModel):
    id: str


class ExecuteHistoryResponse(BaseModel):
    url: Optional[str] = None
    created_at: Optional[str] = None
    end_time: Optional[str] = None
    current: Optional[str] = None
    latest_commit: Optional[str] = None
    id: str
    topo: str
    log: str
    user: str
    executed: str
    status: str
    statistic: Optional[Dict[str, Any]] = None


class CaseCombinationsResponse(BaseModel):
    id: str
    name: str
    created_at: str
    cases: List[str] = None
    user: str


class CaseCombinationsRequest(BaseModel):
    name: str
    cases: List[str] = None


class combinationShareRequest(BaseModel):
    share_user: str