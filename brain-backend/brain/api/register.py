# Copyright (C) 2021 - 2025, Shanghai Yunsilicon Technology Co., Ltd.
# All rights reserved.

import importlib
import pkgutil
import logging
from fastapi import FastAPI

LOG = logging.getLogger(__name__)


def register_routers(app: FastAPI):
    routers_package = "brain.api.routers"

    try:
        routers_module = importlib.import_module(routers_package)

        for _, module_name, is_pkg in pkgutil.iter_modules(routers_module.__path__):
            if is_pkg or module_name.startswith('__'):
                continue

            if module_name.endswith('.py'):
                module_name = module_name[:-3]

            try:
                module = importlib.import_module(f"{routers_package}.{module_name}")

                router = None
                for possible_name in ['router', f'{module_name}_router', 'api_router']:
                    if hasattr(module, possible_name):
                        router = getattr(module, possible_name)
                        break

                if router:
                    tag_name = module_name.replace('_router', '')
                    app.include_router(router, tags=[tag_name])
                    LOG.debug(f"Registered router: {module_name}")
                else:
                    LOG.debug(f"No router found in module: {module_name}")

            except ImportError as e:
                LOG.error(f"Failed to import module {module_name}: {e}")
            except Exception as e:
                LOG.error(f"Error registering router {module_name}: {e}")

    except ImportError:
        LOG.error(f"Router package not found: {routers_package}")