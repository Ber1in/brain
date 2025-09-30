# Copyright (C) 2021 - 2025, Shanghai Yunsilicon Technology Co., Ltd.
# All rights reserved.

from fastapi.middleware.cors import CORSMiddleware
import os
from fastapi import applications
from fastapi import FastAPI as FastAPIBase
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.staticfiles import StaticFiles


class FastAPI(FastAPIBase):
    """Swagger UI uses resources in the local brain/static directory"""

    def __init__(self, *args, **kwargs) -> None:
        if "swagger_js_url" in kwargs:
            self.swagger_js_url = kwargs.pop("swagger_js_url")
        if "swagger_css_url" in kwargs:
            self.swagger_css_url = kwargs.pop("swagger_css_url")
        if "swagger_favicon_url" in kwargs:
            self.swagger_favicon_url = kwargs.pop("swagger_favicon_url")

        def get_swagger_ui_html_with_local_file(*args, **kwargs):
            return get_swagger_ui_html(
                *args,
                **kwargs,
                swagger_js_url=self.swagger_js_url,
                swagger_css_url=self.swagger_css_url,
                swagger_favicon_url=self.swagger_favicon_url,
            )

        applications.get_swagger_ui_html = get_swagger_ui_html_with_local_file
        super(FastAPI, self).__init__(*args, **kwargs)


app = FastAPI(
    title="Brain API",
    swagger_js_url="/static/swagger-ui/swagger-ui-bundle.js",
    swagger_css_url="/static/swagger-ui/swagger-ui.css",
    swagger_favicon_url="/static/favicon.png"
)
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")


# 允许前端访问的源
origins = [
    "http://10.0.3.206:8000",  # 你前端地址
    "http://localhost:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,      # 允许的源
    allow_credentials=True,
    allow_methods=["*"],        # 允许所有方法 GET, POST...
    allow_headers=["*"],        # 允许所有请求头
)
