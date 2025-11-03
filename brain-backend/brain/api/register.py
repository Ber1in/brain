# Copyright (C) 2021 - 2025, Shanghai Yunsilicon Technology Co., Ltd.
# All rights reserved.

import importlib
import pkgutil
import logging
from fastapi import FastAPI

LOG = logging.getLogger(__name__)


def discover_router_packages(base_package: str = "brain.api"):
    """Discover all subpackages ending with .routers under base_package"""
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
        try:
            sub_module = importlib.import_module(sub_pkg)
        except ImportError:
            continue

        for _, sub_name, sub_is_pkg in pkgutil.iter_modules(sub_module.__path__):
            if sub_is_pkg and sub_name == "routers":
                router_packages.append(f"{sub_pkg}.routers")

    return router_packages


def register_routers(app: FastAPI):
    router_packages = discover_router_packages()

    for routers_package in router_packages:
        try:
            routers_module = importlib.import_module(routers_package)

            for _, module_name, is_pkg in pkgutil.iter_modules(routers_module.__path__):
                if is_pkg or module_name.startswith("__"):
                    continue

                if module_name.endswith(".py"):
                    module_name = module_name[:-3]

                try:
                    module = importlib.import_module(f"{routers_package}.{module_name}")

                    router = None
                    for possible_name in ["router", f"{module_name}_router", "api_router"]:
                        if hasattr(module, possible_name):
                            router = getattr(module, possible_name)
                            break

                    if router:
                        tag_name = module_name.replace("_router", "")

                        # version prefix logic
                        version = routers_package.split(".")[-2]  # v1, v2, v3, internal
                        prefix = "" if version == "v1" else f"/{version}"

                        app.include_router(router, prefix=prefix, tags=[tag_name])
                        LOG.debug(f"Registered router: {routers_package}.{module_name} "
                                  f"(prefix={prefix})")
                    else:
                        LOG.debug(f"No router found in module: {module_name}")

                except ImportError as e:
                    LOG.error(f"Failed to import module {module_name}: {e}")
                except Exception as e:
                    LOG.error(f"Error registering router {module_name}: {e}")

        except ImportError:
            LOG.error(f"Router package not found: {routers_package}")