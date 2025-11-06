# Copyright (C) 2021 - 2025, Shanghai Yunsilicon Technology Co., Ltd.
# All rights reserved.

import random
from uuid import uuid4
from fastapi import APIRouter, Depends, status, HTTPException
import logging


from brain.auth import authenticate_user
from brain.api.v2.schemas import tag_schemas
from brain.json_db import SQLiteDocumentDB

LOG = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(authenticate_user)])
TAG_COLLERCTION = "tags"
db = SQLiteDocumentDB()


@router.post("/tag", status_code=status.HTTP_201_CREATED, response_model=tag_schemas.TagsRequest)
async def create_tags(data: tag_schemas.TagsRequest):
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


@router.get("/tags", response_model=tag_schemas.TagsResponse)
async def get_all_tags():
    all_tags = db.find(TAG_COLLERCTION)
    LOG.info(f"Fetched all tags: {all_tags}")
    return {"tags": all_tags}


@router.delete("/tag/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tag(tag_id: str):
    exist = db.find(TAG_COLLERCTION, {"id": tag_id})
    if not exist:
        LOG.warning(f"Tag not found: ID={tag_id}")
        raise HTTPException(status_code=404, detail=f"Tag with ID '{tag_id}' not found")

    db.delete(TAG_COLLERCTION, {"id": tag_id})
    LOG.info(f"Tag deleted: ID={tag_id}")