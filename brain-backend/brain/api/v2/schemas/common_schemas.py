# Copyright (C) 2021 - 2025, Shanghai Yunsilicon Technology Co., Ltd.
# All rights reserved.

from pydantic import BaseModel, Field
from typing import List


class TagsRequest(BaseModel):
    name: str


class TagResponse(TagsRequest):
    name: str
    color: str
    id: str


class TagsResponse(BaseModel):
    tags: List[TagResponse]


class RemoteFSResponse(BaseModel):
    type: str
    name: str


class TaskStatusResponse(BaseModel):
    id: str
    server_id: str
    status: str
    stage: str
    detail: str
    timestamp: str
    mcr: str
    option: str


class ResetFwRequest(BaseModel):
    path: str


class MCRRequest(ResetFwRequest):
    update_options: str = Field(None)


class FilteringConditions(BaseModel):
    only_focus: int = 0
    tags: List[str] = []
    tag_filtering_condition: str = ""
    nics: List[str] = []
    nic_filtering_condition: str = ""


class OperationFilterRequest(BaseModel):
    user: str = None
    start: str = None
    end: str = None
    operation: str = None


class OperationResponse(BaseModel):
    request_id: str = None
    user: str = None
    path: str = None
    method: str = None
    status: str = None
    date: str = None


class InstallDetailResponse(BaseModel):
    name: str = None
    arg_name: str = None