# Copyright (C) 2021 - 2025, Shanghai Yunsilicon Technology Co., Ltd.
# All rights reserved.

import asyncio
from contextlib import contextmanager
import subprocess
from typing import Dict, List
from datetime import datetime
import os
from pathlib import Path
from uuid import uuid4
import gitlab
import git
import logging
import yaml
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks

from brain.config import settings
from brain.auth import authenticate_user
from brain.utils.collect_cases import collect_tests_with_detailed_report
from brain.api.v2.schemas import yuntester_schemas
from brain.json_db import SQLiteDocumentDB

router = APIRouter(dependencies=[Depends(authenticate_user)])
log_router = APIRouter()
LOG = logging.getLogger(__name__)

IGNORE_DIRS = ["__pycache__", ".pytest_cache", ".git", ".idea"]
GITLAB_URL = 'https://git-sha.yunsilicon.com'
PRIVATE_TOKEN = 'TaZqU7hppbrNsfFx-w4j'
PROJECT_PATH = 'yunsilicon-software/yuntester'
SERVER_COLLECTION = "servers"
TEST_CASE_COLLECTION = "test_cases"
TEST_HISTORY_COLLECTION = "test_history"
TEST_DATA_DIR = "/opt/yunTesterData"
BMC_USER = "ipmiadmin"
BMC_PASS = "ymxl@2022"
db = SQLiteDocumentDB()


async def get_user_repo_dir(user: str) -> str:
    """Return the repo directory for the given user."""
    user_repo_dir = os.path.join(TEST_DATA_DIR, user, "yuntester")
    os.makedirs(os.path.dirname(user_repo_dir), exist_ok=True)
    return user_repo_dir


async def get_user_log_dir(user: str) -> str:
    """Return the repo directory for the given user."""
    logs_dir = os.path.join(TEST_DATA_DIR, user, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    return logs_dir


async def get_user_topo_dir(user: str) -> str:
    """Return the repo directory for the given user."""
    topo_dir = os.path.join(TEST_DATA_DIR, user, "topo")
    os.makedirs(topo_dir, exist_ok=True)
    return topo_dir


async def get_user_result_dir(user: str) -> str:
    """Return the repo directory for the given user."""
    result_dir = os.path.join(TEST_DATA_DIR, user, "results")
    os.makedirs(result_dir, exist_ok=True)
    return result_dir


async def get_current_code_and_commit(user):
    user_repo_dir = await get_user_repo_dir(user)
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


@router.get("/yuntester/branchs-tags", response_model=yuntester_schemas.BranchAndTagResponse)
async def get_repo_branches_and_tags(user=Depends(authenticate_user)):
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

    user_repo_dir = await get_user_repo_dir(user)

    try:
        if not os.path.exists(user_repo_dir):
            LOG.info("Repo does not exist, cloning...")
            clone_url = (
                f"https://oauth2:{PRIVATE_TOKEN}@git-sha.yunsilicon.com/{PROJECT_PATH}.git")
            git.Repo.clone_from(clone_url, user_repo_dir)
        else:
            LOG.debug("Repo exists, skip cloning")

        current, latest_commit = await get_current_code_and_commit(user)
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


@router.post("/yuntester/switch", status_code=204)
async def switch_branch_or_tag(data: yuntester_schemas.CheckoutRequest,
                               user=Depends(authenticate_user)):
    LOG.info(f"{user} witching to branch={data.branch} tag={data.tag}")

    try:
        user_repo_dir = await get_user_repo_dir(user)
        repo = git.Repo(user_repo_dir)

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


@router.post("/yuntester/commands", response_model=yuntester_schemas.CasesResponse)
async def get_test_cases(data: yuntester_schemas.DirNeedCollectRequest, 
                         user=Depends(authenticate_user)):
    LOG.info(f"{user} collecting tests from: {data.dirs}")

    user_repo_dir = await get_user_repo_dir(user)
    commands = collect_tests_with_detailed_report(
        data.dirs, user_repo_dir
    )
    return {"cases": commands}


def run_sync_pytest(task_id, cases, test_base_dir, log_path, env_topo_path, result_dir):
    """Execute pytest using subprocess and redirect terminal output to log file"""
    @contextmanager
    def working_directory(path: str):
        original_cwd = os.getcwd()
        try:
            os.chdir(path)
            yield
        finally:
            os.chdir(original_cwd)

    executed_cases = 0
    all_cases = len(cases)

    with working_directory(test_base_dir):
        # Ensure log directory exists
        allure_results_dir = os.path.join(result_dir, "allure-results")
        os.makedirs(os.path.dirname(os.path.abspath(log_path)), exist_ok=True)
        os.makedirs(allure_results_dir, exist_ok=True)

        for idx, case in enumerate(cases, 1):
            LOG.debug(f"Executing test case {idx}/{all_cases}: {case}")

            # Construct pytest command
            cmd = ["pytest", "-q", "-s", "-v", case, "--env",
                   env_topo_path, "--alluredir", allure_results_dir]

            try:
                with open(log_path, 'a', encoding='utf-8') as log_file:
                    subprocess.run(
                        cmd,
                        stdout=log_file,
                        stderr=subprocess.STDOUT,  # merge stderr to stdout
                        text=True,
                        encoding='utf-8',
                        cwd=test_base_dir,
                        timeout=7200  # 2 hour timeout
                    )

            except subprocess.TimeoutExpired:
                LOG.error(f"Test case {case} execution timeout")
            except Exception as e:
                LOG.error(f"Error executing test case {case}: {e}")

            executed_cases += 1

            # Update execution progress to database
            try:
                db.update(TEST_HISTORY_COLLECTION, {"id": task_id}, 
                          {"executed": f"{executed_cases}/{all_cases}"})
            except Exception as e:
                LOG.error(f"Failed to update database: {e}")

        try:
            allure_report_dir = os.path.join(result_dir, "allure-report")

            subprocess.run(
                ["allure", "generate", allure_results_dir, "-c", "-o", allure_report_dir],
                check=True,
                timeout=600,
                cwd=test_base_dir
            )

            LOG.info(f"Allure report generated at {allure_report_dir}")

        except subprocess.CalledProcessError as e:
            LOG.warning(f"Allure report generation failed with exit code {e.returncode}")
        except subprocess.TimeoutExpired:
            LOG.warning("Allure report generation timeout")
        except Exception as e:
            LOG.warning(f"Error generating Allure report: {e}")


async def execute_test_task(task_id: str, cases: list, user: str,
                            env_topo_path: str, log_path: str, result_dir: str):

    try:
        db.update(TEST_HISTORY_COLLECTION, {"id": task_id}, {"status": "running"})
        test_base_dir = await get_user_repo_dir(user)

        if not os.path.exists(test_base_dir):
            raise Exception(f"Test directory not found: {test_base_dir}")

        await asyncio.to_thread(
            run_sync_pytest,
            task_id, cases, test_base_dir, log_path, env_topo_path, result_dir
        )

        end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        db.update(
            TEST_HISTORY_COLLECTION, {"id": task_id}, {"status": "success", "end_time": end_time})

        LOG.info(f"Test task {task_id} completed successfully")

    except Exception as e:
        end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        db.update(
            TEST_HISTORY_COLLECTION, {"id": task_id}, {"status": "failed", "end_time": end_time})
        LOG.error(f"Test task {task_id} failed: {str(e)}")


async def prepare_test_environment(data, user, dt):
    def normalize_nic_type(t: str) -> str:
        t = t or ""
        if t == "metaScale-200 OCP3.0":
            return "ms200-ocp3.0"
        return t.split("-")[0].upper()

    clients = {}

    host_num = 0
    for server in data.servers:
        server_info = db.find_one(SERVER_COLLECTION, {"id": server.device_id})
        client_info = {
            "host": server_info["device"]["ip"],
            "username": server_info["device"]["username"],
            "password": server_info["device"]["password"],
            "keyfile": "/root/.ssh/id_rsa",
            "ssh_port": 22,
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
                "type": normalize_nic_type(nic.type),
                "mac": nic.mac
            }
            nics.append(nic_info)
        if nics:
            client_info["nics"] = nics
        host_num += 1
        clients[f"host{host_num}"] = client_info

    env_info = {}
    env_info.update(clients)

    user_topo_dir = await get_user_topo_dir(user)
    env_topo_path = os.path.join(user_topo_dir, f'{dt}.yaml')

    try:
        with open(env_topo_path, "w") as f:
            yaml.safe_dump(env_info, f, default_flow_style=False, allow_unicode=True)
        LOG.info(f"env info has been saved to YAML: {env_topo_path}")
    except Exception as e:
        LOG.error("Failed to save YAML: %s", str(e))
        raise HTTPException(status_code=500, detail="Failed to save YAML")

    return env_topo_path


@router.post("/yuntester/execute-cases", response_model=yuntester_schemas.ExecuteResponse)
async def execute_cases(data: yuntester_schemas.ExecuteRequest,
                        background: BackgroundTasks,
                        user=Depends(authenticate_user)):
    task_id = str(uuid4())
    start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    dt = start_time.replace("-", "").replace(" ", "_").replace(":", "")

    env_topo_filename = await prepare_test_environment(data, user, dt)

    log_filename = dt + ".log"
    log_dir = await get_user_log_dir(user)
    log_path = os.path.join(log_dir, log_filename)
    result_base_dir = await get_user_result_dir(user)
    result_dir = os.path.join(result_base_dir, dt)
    env_topo_filename = f'{dt}.yaml'

    current, latest_commit = await get_current_code_and_commit(user,)

    task_record = {
        "id": task_id,
        "status": "pending",
        "user": user,
        "current": current,
        "latest_commit": latest_commit,
        "created_at": start_time,
        "executed": "",
        "end_time": "",
        "url": f"{settings.file_server}/qa-auto-files/{user}/results/{dt}/allure-report/index.html",
        "topo": f"{settings.file_server}/qa-auto-files/{user}/topo/{env_topo_filename}",
        "log": f"{settings.file_server}/qa-auto-files/{user}/logs/{log_filename}",
    }

    db.insert(TEST_HISTORY_COLLECTION, task_record)

    background.add_task(
        execute_test_task,
        task_id=task_id,
        cases=data.cases,
        user=user,
        env_topo_path=env_topo_filename,
        log_path=log_path,
        result_dir=result_dir
    )

    LOG.info(f"Test task {task_id} submitted for user {user}")

    return {"id": task_id}


@router.get("/yuntester/task/{task_id}", response_model=yuntester_schemas.ExecuteHistoryResponse)
async def get_task_status(task_id: str):
    task = db.find_one(TEST_HISTORY_COLLECTION, {"id": task_id})

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return task


@router.get("/yuntester/execute-history",
            response_model=List[yuntester_schemas.ExecuteHistoryResponse])
async def execute_history(user=Depends(authenticate_user)):
    """Retrieve execution history for the authenticated user."""

    LOG.info(f"Fetching execution history for user={user}")
    history = db.find(TEST_HISTORY_COLLECTION, {"user": user})

    LOG.info(f"Fetched {len(history)} execution history records for user={user}")
    return history


@router.get("/yuntester/custom-combinations", 
            response_model=List[yuntester_schemas.CaseCombinationsResponse])
async def list_custom_combinations_of_test_cases(user=Depends(authenticate_user)):
    """There are many user-defined sets of test cases, and the current interface
    is used to query these combinations."""

    LOG.info(f"Fetching all custom test case combinations for user={user}")
    all_combinations = db.find(TEST_CASE_COLLECTION, {"user": user})

    LOG.info(f"Fetched {len(all_combinations)} combinations")
    return all_combinations


@router.post("/yuntester/custom-combinations", status_code=204)
async def save_custom_combinations_of_test_cases(
        data: yuntester_schemas.CaseCombinationsRequest, user=Depends(authenticate_user)):
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


@router.delete("/yuntester/custom-combinations/{combination_id}", status_code=204)
async def delete_custom_combination(combination_id: str):
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


@router.post("/yuntester/custom-combinations/{combination_id}", status_code=204)
async def copy_custom_combination(combination_id: str,
                                  data: yuntester_schemas.combinationShareRequest):
    """Copy a custom test case combination and share it with another user."""

    try:
        record = db.find_one(TEST_CASE_COLLECTION, {"id": combination_id})
    except Exception:
        LOG.warning("Custom combination not found: id=%s", combination_id)
        raise HTTPException(status_code=404, detail="Combination not found")

    try:
        new_id = str(uuid4())
        record["id"] = new_id
        record["user"] = data.share_user
        db.insert(TEST_CASE_COLLECTION, record)
        LOG.info("Successfully shared combination new_id=%s to user=%s", new_id, data.share_user)
    except Exception as e:
        LOG.error("Failed to insert cloned combination new_id=%s, error=%s", new_id, e)
        raise HTTPException(status_code=500, detail="Failed to save cloned combination")


@router.get("/yuntester/directory-tree")
async def get_directory_tree(user=Depends(authenticate_user)):
    """Get the directory tree of the test code repository (recursive scan, directory-only).
    Node 'name' contains only the current directory name.
    Returned 'path' strips the user repo prefix.
    """

    user_repo_dir = await get_user_repo_dir(user)
    base_path = Path(user_repo_dir)
    products_path = base_path / "testcase"

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
