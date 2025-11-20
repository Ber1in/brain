# Copyright (C) 2021 - 2025, Shanghai Yunsilicon Technology Co., Ltd.
# All rights reserved.

from typing import Dict, List
from datetime import datetime
import os
from pathlib import Path
from uuid import uuid4
import gitlab
import git
import logging
import yaml
from fastapi import APIRouter, Depends, HTTPException

from brain.auth import authenticate_user
from brain.utils.collect_cases import collect_tests_with_detailed_report
from brain.api.v2.schemas import qa_schemas
from brain.json_db import SQLiteDocumentDB

router = APIRouter(dependencies=[Depends(authenticate_user)])
LOG = logging.getLogger(__name__)

IGNORE_DIRS = {"__pycache__", ".pytest_cache", ".git", ".idea"}
GITLAB_URL = 'https://git-sha.yunsilicon.com'
PRIVATE_TOKEN = 'qZb5uFi8JfxLNmXnvtWW'
PROJECT_PATH = 'yunsilicon-software/qa_auto'
SERVER_COLLECTION = "servers"
TEST_CASE_COLLECTION = "test_cases"
TEST_HISTORY_COLLECTION = "test_history"
BMC_USER = "ipmiadmin"
BMC_PASS = "ymxl@2022"
db = SQLiteDocumentDB()


def get_user_repo_dir(user: str) -> str:
    """Return the repo directory for the given user."""
    user_repo_dir = f"/tmp/{user}/qa_auto"
    os.makedirs(os.path.dirname(user_repo_dir), exist_ok=True)
    return user_repo_dir


def get_user_log_dir(user: str) -> str:
    """Return the repo directory for the given user."""
    logs_dir = f"/tmp/{user}/logs"
    os.makedirs(logs_dir, exist_ok=True)
    return logs_dir


def get_user_topo_dir(user: str) -> str:
    """Return the repo directory for the given user."""
    topo_dir = f"/tmp/{user}/topo"
    os.makedirs(topo_dir, exist_ok=True)
    return topo_dir


def get_user_result_dir(user: str) -> str:
    """Return the repo directory for the given user."""
    result_dir = f"/tmp/{user}/results"
    os.makedirs(result_dir, exist_ok=True)
    return result_dir


def get_current_code_and_commit(user):
    user_repo_dir = get_user_repo_dir(user)
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
    return current, latest_commit 


@router.get("/qa_auto/branchs-tags", response_model=qa_schemas.BranchAndTagResponse)
def get_repo_branches_and_tags(user=Depends(authenticate_user)):
    gl = gitlab.Gitlab(GITLAB_URL, private_token=PRIVATE_TOKEN)
    LOG.info(f"Query branch and tag information for {user}")
    gl.auth()

    branchs, tags = [], []
    project = gl.projects.get(PROJECT_PATH)

    # list branches
    for branch in project.branches.list(all=True):
        branchs.append(branch.name)

    # list tags
    for tag in project.tags.list(all=True):
        tags.append(tag.name)

    user_repo_dir = get_user_repo_dir(user)

    try:
        if not os.path.exists(user_repo_dir):
            LOG.info("Repo does not exist, cloning...")
            clone_url = (
                f"https://oauth2:{PRIVATE_TOKEN}@git-sha.yunsilicon.com/{PROJECT_PATH}.git")
            git.Repo.clone_from(clone_url, user_repo_dir)
        else:
            LOG.debug("Repo exists, skip cloning")

        current, latest_commit = get_current_code_and_commit(user)
        LOG.info(f"current={current} latest={latest_commit}")

    except Exception as e:
        LOG.error(f"Failed to read repo for {user}: {e}")
        current = None
        latest_commit = None

    return {
        "branchs": branchs,
        "tags": tags,
        "current": current,
        "latest_commit": latest_commit,
    }


@router.post("/qa_auto/switch", status_code=204)
def switch_branch_or_tag(data: qa_schemas.CheckoutRequest, user=Depends(authenticate_user)):
    LOG.info(f"{user} witching to branch={data.branch} tag={data.tag}")

    try:
        repo_path = get_user_repo_dir(user)
        repo = git.Repo(repo_path)

        repo.git.fetch("--all", "--tags")
        LOG.info("Fetch completed")

        if data.branch:
            branch = data.branch
            LOG.info(f"Switching to branch {branch}")

            if branch not in [h.name for h in repo.heads]:
                LOG.info(f"Branch {branch} not found, creating")
                repo.git.checkout("-b", branch, f"origin/{branch}")
            else:
                repo.git.checkout(branch)

            repo.git.pull()
            LOG.info(f"Branch {branch} updated")

        elif data.tag:
            tag = data.tag
            LOG.info(f"Switching to tag {tag}")

            if tag not in [t.name for t in repo.tags]:
                LOG.warning(f"Tag {tag} not found")
                raise HTTPException(status_code=404, detail=f"Tag '{tag}' not found")

            repo.git.checkout(f"tags/{tag}")
            LOG.info(f"Switched to tag {tag}")

    except Exception as e:
        LOG.error(f"Switch failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to switch: {e}")


@router.post("/qa_auto/commands", response_model=qa_schemas.CasesResponse)
def get_test_cases(data: qa_schemas.DirNeedCollectRequest, user=Depends(authenticate_user)):
    LOG.info(f"{user} collecting tests from: {data.dirs}")

    commands = collect_tests_with_detailed_report(
        data.dirs,
        get_user_repo_dir(user)
    )
    return {"cases": commands}


@router.post("/qa_auto/execute-cases", response_model=qa_schemas.ExecuteResponse)
def execute_cases(data: qa_schemas.ExecuteRequest, user=Depends(authenticate_user)):

    def normalize_nic_type(t: str) -> str:
        t = t or ""
        if t == "metaScale-200 OCP3.0":
            return "ms200-ocp3.0"
        return t.split("-")[0].lower()

    clients = []

    for server in data.servers:
        server_info = db.find_one(SERVER_COLLECTION, {"id": server.device_id})
        client_info = {
            "host": server_info["device"]["ip"],
            "username": server_info["device"]["username"],
            "password": server_info["device"]["password"],
            "keyfile": "/root/.ssh/id_rsa",
            "ipmi": {
                "ip": server_info["bmc"]["ip"],
                "username": BMC_USER,
                "password": BMC_PASS
            }
        }

        nics = []
        for nic in server.nics:
            nic_info = {
                "ifname": nic.iface,
                "bdf": nic.bdf,
                "type": normalize_nic_type(nic.type)
            }
            nics.append(nic_info)
        if nics:
            client_info["nics"] = nics
        clients.append(client_info)

    env_info = {"yaml_version": "v1", "clients": clients}

    start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    dt = start_time.replace("-", "").replace(" ", "_").replace(":", "")
    env_topo_filename = dt + ".yaml"
    log_filename = dt + ".log"

    env_topo_path = os.path.join(get_user_topo_dir(user), env_topo_filename)
    log_path = os.path.join(get_user_log_dir(user), log_filename)

    try:
        with open(env_topo_path, "w") as f:
            yaml.safe_dump(env_info, f, default_flow_style=False, allow_unicode=True)
        LOG.info(f"env info has been saved to YAML: {env_topo_path}")
    except Exception as e:
        LOG.error("Failed to save YAML: %s", str(e))
        raise HTTPException(status_code=500, detail="Failed to save YAML")

    # pytest -s -v    xxx/xxx/xx.py::xxxx:xxx      --env_config xxxx.yaml  --alluredir= xxx/xxxx/xxxx

    current, latest_commit = get_current_code_and_commit(user)
    record = {"url": f"/qa-auto-files/{user}/results/tmp_report.html", 
              "time": start_time,
              "current": current,
              "latest_commit": latest_commit,
              "id": str(uuid4()),
              "topo": f"/qa-auto-files/{user}/topo/{env_topo_filename}",
              "log": f"/qa-auto-files/{user}/logs/{log_filename}",
              "user": user}
    db.insert(TEST_HISTORY_COLLECTION, record)
    LOG.info("Test case execution records have been logged.")

    return record


@router.get("/qa_auto/execute-history", response_model=List[qa_schemas.ExecuteResponse])
def execute_history(user=Depends(authenticate_user)):
    """Retrieve execution history for the authenticated user."""

    LOG.info(f"Fetching execution history for user={user}")
    history = db.find(TEST_HISTORY_COLLECTION, {"user": user})

    LOG.info(f"Fetched {len(history)} execution history records for user={user}")
    return history


@router.get("/qa_auto/custom-combinations", 
            response_model=List[qa_schemas.CaseCombinationsResponse])
def list_custom_combinations_of_test_cases(user=Depends(authenticate_user)):
    """There are many user-defined sets of test cases, and the current interface
    is used to query these combinations."""

    LOG.info(f"Fetching all custom test case combinations for user={user}")
    all_combinations = db.find(TEST_CASE_COLLECTION, {"user": user})

    LOG.info(f"Fetched {len(all_combinations)} combinations")
    return all_combinations


@router.post("/qa_auto/custom-combinations", status_code=204)
def save_custom_combinations_of_test_cases(
        data: qa_schemas.CaseCombinationsRequest, user=Depends(authenticate_user)):
    """
    Save a new user-defined combination of test cases.

    This endpoint receives a combination definition, generates metadata such as
    creation timestamp and a unique ID, and persists it into the database.
    """

    data_dict = data.dict()
    LOG.info(f"Saving a new custom test case combination: {data_dict}")

    data_dict["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data_dict["id"] = str(uuid4())
    data_dict["user"] = user

    db.insert(TEST_CASE_COLLECTION, data_dict)

    LOG.info(f"Custom combination saved with id={data_dict['id']}")


@router.delete("/qa_auto/custom-combinations/{combination_id}", status_code=204)
def delete_custom_combination(combination_id: str):
    """
    Delete a user-defined combination of test cases by its ID.

    This endpoint removes a previously saved test case combination from the
    database. If the specified ID does not exist, a 404 error is raised.
    """

    LOG.info(f"Request to delete custom test case combination: id={combination_id}")

    try:
        record = db.find_one(TEST_CASE_COLLECTION, {"id": combination_id})
    except Exception:
        LOG.warning("Custom combination not found: id=%s", combination_id)
        raise HTTPException(status_code=404, detail="Combination not found")

    try:
        db.delete(TEST_CASE_COLLECTION, {"id": combination_id})
        LOG.info(
            f"Custom combination deleted successfully: id={combination_id}, name={record['name']}")
    except Exception as e:
        LOG.error("Failed to delete combination id=%s, error=%s", combination_id, e)
        raise HTTPException(status_code=500, detail=f"Deletion failed: {e}")


@router.get("/qa_auto/directory-tree")
def get_directory_tree(user=Depends(authenticate_user)):
    """Get the directory tree of the test code repository (recursive scan, directory-only).
    Node 'name' contains only the current directory name.
    Returned 'path' strips the user repo prefix.
    """

    user_repo_dir = get_user_repo_dir(user)
    base_path = Path(user_repo_dir)
    products_path = base_path / "products"

    LOG.info(f"Building directory tree for user={user} at base_path={products_path}")

    prefix_len = len(str(base_path)) + 1

    def strip_prefix(path: Path) -> str:
        p = str(path)
        return p[prefix_len:] if p.startswith(str(base_path)) else p

    def build_node(p: Path) -> Dict:
        LOG.debug(f"Scanning directory: {p}")

        node = {
            "name": p.name,
            "path": strip_prefix(p),
            "type": "directory",
            "children": []
        }
        try:
            for item in sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name)):
                if not item.is_dir():
                    continue

                if item.name in IGNORE_DIRS:
                    LOG.debug(f"Skipping ignored directory: {item}")
                    continue

                node["children"].append(build_node(item))

        except PermissionError:
            LOG.warning(f"Permission denied while scanning: {p}")

        return node

    tree = []
    if products_path.exists() and products_path.is_dir():
        tree.append(build_node(products_path))
    else:
        LOG.warning(f"Products directory does not exist for user={user}: {products_path}")

    LOG.info(f"Directory tree built for user={user}, total root nodes={len(tree)}")

    return {"tree": tree}
