# Copyright (C) 2021 - 2025, Shanghai Yunsilicon Technology Co., Ltd.
# All rights reserved.

import importlib
import pkgutil
import logging
import os
from fastapi import FastAPI


LOG = logging.getLogger(__name__)

API_PREFIX = {
    "v1": "",
    "v2": "/api"
}

ENABLE_API_V1 = os.getenv("ENABLE_API_V1", "true").lower() == "true"
ENABLE_API_V2 = os.getenv("ENABLE_API_V2", "true").lower() == "true"


def _register_module_router(app, module, routers_package, module_name):
    router = None
    for possible_name in ["router", f"{module_name}_router", "api_router"]:
        if hasattr(module, possible_name):
            router = getattr(module, possible_name)
            break

    if not router:
        return

    tag_name = module_name.replace("_router", "")
    version = routers_package.split(".")[-2]
    prefix = API_PREFIX.get(version, "")

    app.include_router(router, prefix=prefix, tags=[tag_name])
    LOG.debug(f"Registered router: {routers_package}.{module_name} (prefix: {prefix})")


def discover_router_packages(base_package: str = "brain.api"):
    router_packages = []
    try:
        base_module = importlib.import_module(base_package)
    except ImportError:
        LOG.error(f"Base API package not found: {base_package}")
        return router_packages

    for _, pkg_name, is_pkg in pkgutil.iter_modules(base_module.__path__):
        if not is_pkg:
            continue

        sub_pkg = f"{base_package}.{pkg_name}"

        if pkg_name == "auth_router":
            continue

        if pkg_name == "v1" and not ENABLE_API_V1:
            LOG.warning("Skipping v1 APIs by config")
            continue
        if pkg_name == "v2" and not ENABLE_API_V2:
            LOG.warning("Skipping v2 APIs by config")
            continue

        try:
            sub_module = importlib.import_module(sub_pkg)
        except ImportError:
            continue

        for _, sub_name, sub_is_pkg in pkgutil.iter_modules(sub_module.__path__):
            if sub_is_pkg and sub_name == "routers":
                router_packages.append(f"{sub_pkg}.routers")

    return router_packages


def register_routers(app: FastAPI):
    try:
        auth_module = importlib.import_module("brain.api.auth_router")
        _register_module_router(app, auth_module, "brain.api", "auth_router")

    except Exception as e:
        LOG.error(f"Failed loading auth_router: {e}")

    router_packages = discover_router_packages()
    for routers_package in router_packages:
        try:
            routers_module = importlib.import_module(routers_package)
            for _, module_name, is_pkg in pkgutil.iter_modules(routers_module.__path__):
                if is_pkg or module_name.startswith("__"):
                    continue

                try:
                    module = importlib.import_module(f"{routers_package}.{module_name}")
                    _register_module_router(app, module, routers_package, module_name)
                except Exception as e:
                    LOG.error(f"Error registering router {module_name}: {e}")

        except ImportError:
            LOG.error(f"Router package not found: {routers_package}")
