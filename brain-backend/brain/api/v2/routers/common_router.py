# Copyright (C) 2021 - 2025, Shanghai Yunsilicon Technology Co., Ltd.
# All rights reserved.

import random
from typing import List
from uuid import uuid4
from fastapi import APIRouter, Depends, status, HTTPException
import logging


from brain.auth import authenticate_user
from brain.api.v2.schemas import common_schemas
from brain.json_db import SQLiteDocumentDB
from brain.utils.ssh_client import AsyncRemoteFS

LOG = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(authenticate_user)])
TAG_COLLERCTION = "tags"
TASK_POOL_COLLECTION = "tasks"
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
