# Copyright (C) 2021 - 2025, Shanghai Yunsilicon Technology Co., Ltd.
# All rights reserved.

import os
import yaml
import random
from typing import List
from uuid import uuid4
from fastapi import APIRouter, Depends, status, HTTPException, Query
import logging


from brain.auth import authenticate_user
from brain.api.v2.schemas import common_schemas
from brain.json_db import SQLiteDocumentDB
from brain.utils import common_utils
from brain.utils.ssh_client import AsyncRemoteFS
from brain.config import AppConfig, CONFIG_FILE, reload_settings, settings, AppConfigResponse

LOG = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(authenticate_user)])
TAG_COLLERCTION = "tags"
TASK_POOL_COLLECTION = "tasks"
OPERATIONAL_AUDIT_COLLECTION = "operational_audit"
TASK_DIY_CONFIG = "users"
db = SQLiteDocumentDB()
COMMON_USER = "tester"
COMMON_USER_PASSWORD = "Test.999"


@router.post("/tag", status_code=status.HTTP_201_CREATED, response_model=common_schemas.TagsRequest)
async def create_tags(data: common_schemas.TagsRequest):
    exist = db.find(TAG_COLLERCTION, {"name": data.name})
    if exist:
        LOG.info(f"Tag already exists: {data.name}")
        raise HTTPException(status_code=400, detail=f"Tag '{data.name}' already exists")

    tag_data = {
        "id": str(uuid4()),
        "name": data.name,
        "color": "#{:06x}".format(random.randint(0, 0xFFFFFF)),
    }
    db.insert(TAG_COLLERCTION, tag_data)
    LOG.info(f"Tag created: {data.name}, ID: {tag_data['id']}")

    return tag_data


@router.get("/tags", response_model=common_schemas.TagsResponse)
async def get_all_tags():
    all_tags = db.find(TAG_COLLERCTION)
    LOG.info(f"Total tags fetched: {len(all_tags)}")
    return {"tags": all_tags}


@router.delete("/tag/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tag(tag_id: str):
    exist = db.find(TAG_COLLERCTION, {"id": tag_id})
    if not exist:
        LOG.warning(f"Tag not found: ID={tag_id}")
        raise HTTPException(status_code=404, detail=f"Tag with ID '{tag_id}' not found")

    db.delete(TAG_COLLERCTION, {"id": tag_id})
    LOG.info(f"Tag deleted: ID={tag_id}")


@router.get("/remotefs/list_dir", response_model=List[common_schemas.RemoteFSResponse])
async def list_dir(path: str):
    items = []
    async with AsyncRemoteFS("10.0.3.248", COMMON_USER, COMMON_USER_PASSWORD) as fs:
        items = await fs.listdir(path)
    return items


@router.get("/tasks/{task_id}", response_model=common_schemas.TaskStatusResponse)
async def query_task_status(task_id: str):
    LOG.debug(f"Querying status for task_id={task_id}")
    try:
        task = db.find_one(TASK_POOL_COLLECTION, {"id": task_id})
        if not task:
            LOG.warning(f"Task {task_id} not found")
            raise HTTPException(status_code=404, detail="task not found")
        LOG.debug(f"Task {task_id} info: {task}")
    except Exception as e:
        LOG.error(f"Failed to query task {task_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to query task")
    return task


@router.get("/settings", response_model=AppConfigResponse)
async def get_settings():
    """Return current global configuration."""
    settings_response = settings.dict()
    settings_response.pop("admin_password")
    settings_response["smtp"].pop("password")
    return settings_response


@router.patch("/settings")
async def patch_settings(data: AppConfig):
    """
    Partially update configuration.
    """

    # Convert global settings to dict
    current = settings.dict()

    # Recursively merge dictionaries
    def deep_update(original, updates):
        for key, value in updates.items():
            if (
                key in original
                and isinstance(original[key], dict)
                and isinstance(value, dict)
            ):
                deep_update(original[key], value)
            else:
                original[key] = value

    deep_update(current, data.dict())

    # Save back to YAML
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        yaml.safe_dump(current, f, allow_unicode=True)

    reload_settings()
    return settings.dict()


@router.post("/filtering_conditions", response_model=common_schemas.FilteringConditions)
async def update_filter_conditions(data: common_schemas.FilteringConditions, 
                                   user=Depends(authenticate_user)):
    try:
        user_info = db.find_one(TASK_DIY_CONFIG, {"user": user})
    except Exception:
        LOG.debug(f"User {user} has not customized server filtering conditions")
        user_info = {
            "id": str(uuid4()),
            "user": user,
            "prefer_servers": data.dict()
        }
        db.insert(TASK_DIY_CONFIG, user_info)
    else:
        user_info["prefer_servers"] = data.dict()
        db.update(TASK_DIY_CONFIG, {"id": user_info["id"]}, user_info)

    return data.dict()


@router.get("/filtering_conditions", response_model=common_schemas.FilteringConditions)
async def get_filter_conditions(user=Depends(authenticate_user)):
    filter_conditions = {}
    try:
        user_info = db.find_one(TASK_DIY_CONFIG, {"user": user})
        filter_conditions = user_info["prefer_servers"]
    except Exception:
        LOG.debug(f"User {user} has not customized server filtering conditions")

    return filter_conditions


@router.get("/operational_audit", response_model=List[common_schemas.OperationResponse])
async def get_operations(user: str = Query(None), start: str = Query(None), end: str = Query(None)):

    try:
        filter_dict = {}

        if user:
            filter_dict["user"] = user

        if start:
            if len(start) == 10:
                start_time = f"{start} 00:00:00"
            else:
                start_time = start
            filter_dict["date >="] = start_time

        if end:
            if len(end) == 10:
                end_time = f"{end} 23:59:59"
            else:
                end_time = end
            filter_dict["date <="] = end_time

        operational_audit = db.find(OPERATIONAL_AUDIT_COLLECTION, filter_dict, 
                                    sort_by="date", desc=True)

        return operational_audit

    except Exception as e:
        LOG.error(f"Failed to retrieve operation audit information, error: {e}")
        raise HTTPException(status_code=500,
                            detail=f"Failed to retrieve operation audit information, error: {e}")


@router.get("/mcr_install_detail", response_model=List[common_schemas.InstallDetailResponse])
async def get_mcr_install_detail(path: str = Query(...)):
    try:
        install_detail = await common_utils.fetch_mcr_install_detail(path)
    except Exception:
        LOG.warning("")
        install_detail = []

    return install_detail