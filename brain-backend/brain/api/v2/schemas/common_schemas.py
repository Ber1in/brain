# Copyright (C) 2021 - 2025, Shanghai Yunsilicon Technology Co., Ltd.
# All rights reserved.

from pydantic import BaseModel
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


class ResetFwRequest(BaseModel):
    path: str


class MCRRequest(ResetFwRequest):
    update_options: str