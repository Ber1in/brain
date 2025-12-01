# Copyright (C) 2021 - 2025, Shanghai Yunsilicon Technology Co., Ltd.
# All rights reserved.

import json
from pydantic import BaseModel, HttpUrl

CONFIG_FILE = "/etc/yuntester/yuntester.json"


class SMTPConfig(BaseModel):
    host: str = "smtp.feishu.cn"
    port: int = 465
    user: str = "yuntester@yunsilicon.com"
    password: str = "VIgB7YFDX9Y3g7Dw"


class AppConfig(BaseModel):
    webhook_url: HttpUrl = (
        "https://webhook.yunsilicon.com/open-apis/bot/v2/hook/51053ced-7d61-4645-95df-f0c6ac3f67a7")
    smtp: SMTPConfig = SMTPConfig()
    yuntester_platform: HttpUrl = "https://yuntester.yunsilicon.com"
    platform_port: int = 8088
    ldap_server: str = "ldaps://it-srv-idc001.yunsilicon.com:636"


def load_config() -> AppConfig:
    """
    Load JSON configuration file and create AppConfig instance.
    Missing fields will use defaults.
    """
    try:
        with open(CONFIG_FILE, "r") as f:
            config_dict = json.load(f)
    except FileNotFoundError:
        config_dict = {}

    for key in ["webhook_url", "yuntester_platform"]:
        if key in config_dict and isinstance(config_dict[key], str):
            config_dict[key] = config_dict[key].rstrip("/")

    return AppConfig(**config_dict)


settings = load_config()
