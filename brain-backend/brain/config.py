# Copyright (C) 2021 - 2025, Shanghai Yunsilicon Technology Co., Ltd.
# All rights reserved.

import yaml
from typing import List, Optional
from pydantic import BaseModel, Field

CONFIG_FILE = "/etc/yuntester/yuntester.yaml"


class SMTPConfig(BaseModel):
    host: str = "smtp.feishu.cn"
    port: int = 465
    user: str = "yuntester@yunsilicon.com"
    password: str = "VIgB7YFDX9Y3g7Dw"


class ReleaseNotice(BaseModel):
    tag: str
    webhook: str


class AppConfig(BaseModel):
    default_webhook: str = (
        "https://webhook.yunsilicon.com/open-apis/bot/v2/hook/51053ced-7d61-4645-95df-f0c6ac3f67a7")
    smtp: SMTPConfig = SMTPConfig()
    yuntester_platform: str = "https://yuntester.yunsilicon.com"
    file_server: str = "https://yuntester-api.yunsilicon.com"
    platform_port: int = 8088
    debug: bool = False
    ldap_server: str = "ldaps://it-srv-idc001.yunsilicon.com:636"
    admin_password: str = "yuntester@admin2021"
    release_notices: Optional[List[ReleaseNotice]] = None
    admin_list: List[str] = Field(default_factory=lambda: [
        "mengxh", "gongyh", "nana", "chenx", "jacky", "zhangx", "weihg"])
    check_heartbeat: bool = True
    heartbeat_interval = 60


def load_config() -> AppConfig:
    """Load YAML configuration file and create AppConfig instance."""
    try:
        with open(CONFIG_FILE, "r") as f:
            config_dict = yaml.safe_load(f) or {}
    except FileNotFoundError:
        config_dict = {}

    for key in ["webhook_url", "yuntester_platform"]:
        if key in config_dict and isinstance(config_dict[key], str):
            config_dict[key] = config_dict[key].rstrip("/")

    return AppConfig(**config_dict)


_current_settings: AppConfig = load_config()


def reload_settings() -> AppConfig:
    """Reload global settings after update and return new settings."""
    global _current_settings
    _current_settings = load_config()
    return _current_settings


class _SettingsProxy:

    @property
    def default_webhook(self) -> str:
        return _current_settings.default_webhook

    @property
    def smtp(self) -> SMTPConfig:
        return _current_settings.smtp

    @property
    def yuntester_platform(self) -> str:
        return _current_settings.yuntester_platform

    @property
    def file_server(self) -> str:
        return _current_settings.file_server

    @property
    def platform_port(self) -> int:
        return _current_settings.platform_port

    @property
    def debug(self) -> bool:
        return _current_settings.debug

    @property
    def ldap_server(self) -> str:
        return _current_settings.ldap_server

    @property
    def admin_password(self) -> str:
        return _current_settings.admin_password

    @property
    def admin_list(self) -> str:
        return _current_settings.admin_list

    @property
    def release_notices(self) -> Optional[List[ReleaseNotice]]:
        return _current_settings.release_notices

    @property
    def check_heartbeat(self) -> bool:
        return _current_settings.check_heartbeat

    @property
    def heartbeat_interval(self) -> bool:
        return _current_settings.heartbeat_interval

    def dict(self):
        return _current_settings.dict()

    def copy(self):
        return _current_settings.copy()

    def json(self, **kwargs):
        return _current_settings.json(**kwargs)


_settings_proxy = _SettingsProxy()

settings = _settings_proxy