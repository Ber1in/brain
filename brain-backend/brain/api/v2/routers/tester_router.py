# Copyright (C) 2021 - 2025, Shanghai Yunsilicon Technology Co., Ltd.
# All rights reserved.

import os
from typing import List
import gitlab
import git
import logging
from fastapi import APIRouter, Depends, HTTPException

from brain.auth import authenticate_user
from brain.utils.collect_cases import collect_tests_with_detailed_report
from brain.api.v2.schemas import qa_schemas

router = APIRouter(dependencies=[Depends(authenticate_user)])
LOG = logging.getLogger(__name__)

GITLAB_URL = 'https://git-sha.yunsilicon.com'
PRIVATE_TOKEN = 'qZb5uFi8JfxLNmXnvtWW'
PROJECT_PATH = 'yunsilicon-software/qa_auto'


@router.get("/qa_auto/branchs-tags", response_model=qa_schemas.BranchAndTagResponse)
def get_repo_branches_and_tags(user=Depends(authenticate_user)):
    gl = gitlab.Gitlab(GITLAB_URL, private_token=PRIVATE_TOKEN)
    gl.auth()

    branchs = []
    tags = []
    project = gl.projects.get(PROJECT_PATH)

    for branch in project.branches.list(all=True):
        branchs.append(branch.name)

    for tag in project.tags.list(all=True):
        tags.append(tag.name)

    user_repo_dir = f"/tmp/{user}/qa_auto"

    try:
        if not os.path.exists(user_repo_dir):
            os.makedirs(os.path.dirname(user_repo_dir), exist_ok=True)
            LOG.info(f"Cloning repository for user {user} into {user_repo_dir}")
            clone_url = f"https://oauth2:{PRIVATE_TOKEN}@git-sha.yunsilicon.com/{PROJECT_PATH}.git"
            git.Repo.clone_from(clone_url, user_repo_dir)

        repo = git.Repo(user_repo_dir)

        if repo.head.is_detached:
            current_commit = repo.head.commit.hexsha
            matched_tag = next(
                (t.name for t in repo.tags if t.commit == repo.head.commit), None
            )
            current = matched_tag or current_commit
        else:
            current = repo.active_branch.name

        latest_commit = repo.head.commit.hexsha

    except Exception as e:
        LOG.warning(f"Failed to determine current branch/tag for user {user}: {e}")
        current = None
        latest_commit = None

    return {"branchs": branchs, "tags": tags, "current": current, "latest_commit": latest_commit}


@router.post("/qa_auto/switch", status_code=204)
def switch_branch_or_tag(data: qa_schemas.CheckoutRequest, user=Depends(authenticate_user)):
    try:
        repo = git.Repo(f"/tmp/{user}/qa_auto")
        repo.git.fetch("--all", "--tags")

        if data.branch:
            branch = data.branch
            if branch not in [h.name for h in repo.heads]:
                repo.git.checkout("-b", branch, f"origin/{branch}")
            else:
                repo.git.checkout(branch)
            repo.git.pull()

        elif data.tag:
            tag = data.tag
            if tag not in [t.name for t in repo.tags]:
                raise HTTPException(status_code=404, detail=f"Tag '{tag}' not found")
            repo.git.checkout(f"tags/{tag}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to switch: {str(e)}")


@router.post("/qa_auto/commands", response_model=qa_schemas.CasesResponse)
def get_test_cases(data: qa_schemas.DirNeedCollectRequest, user=Depends(authenticate_user)):
    LOG.info(f"Starting test collection for: {data.dirs}")
    commands = collect_tests_with_detailed_report(data.dirs, f"/tmp/{user}/qa_auto")
    return {"cases": commands}


@router.post("/qa_auto/execute-cases", response_model=qa_schemas.ExecuteResponse)
def execute_cases(data: qa_schemas.CasesResponse, user=Depends(authenticate_user)):
    return {"url": "https://test.com", "time": ""}


@router.get("/qa_auto/execute-history", response_model=qa_schemas.ExecuteListResponse)
def execute_history(user=Depends(authenticate_user)):
    return {"items": [{"url": "http://10.0.3.206:8088/docs#/", "time": "2025/11/13 11:37:17", 
                       "current": "aidpu_for_mr",
                       "commit": "4854441363f5604a6d8d271d8e40a84f8a2919a0"},
                       {"url": "http://10.0.3.248:8089/", "time": "2025/11/13 11:35:17", 
                       "current": "aidpu_for_mr_11111111111111111111111111222222",
                       "commit": "f6b7c96447942157219b3a3095a54ec51211b975"}]}
