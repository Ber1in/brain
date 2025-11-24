# Copyright (C) 2021 - 2025, Shanghai Yunsilicon Technology Co., Ltd.
# All rights reserved.

from urllib3.util import Retry, Timeout
import time
import logging
from threading import Lock

from brain.clients.ceph import Configuration as CephConfiguration
from brain.clients.ceph import ApiClient as CephApiClient
from brain.clients.ceph.api import auth_api as cephauth
from brain.clients.dpuagent import Configuration as DpuConfiguration
from brain.clients.dpuagent import ApiClient as DpuApiClient
from brain.clients.dpuagent.api import auth_api as dpuagentauth

_ceph_client_pool = {}
_ceph_client_lock = Lock()
_dpuagent_client_pool = {}
_dpuagent_client_lock = Lock()

TOKEN_EXPIRE_SECONDS = 1800  # 30 minutes
LOG = logging.getLogger(__name__)


def get_cephclient(mon_host, username="admin", password="yunsilicon"):
    """
    Return a CephApiClient with valid token.
    Automatically re-login if token is expired.
    """
    now = time.time()
    with _ceph_client_lock:
        cached = _ceph_client_pool.get(mon_host)
        if cached:
            client, acquired_time = cached
            if now - acquired_time < TOKEN_EXPIRE_SECONDS:
                return client  # token still valid

    # Need to login and get a new token
    ceph_cfg = CephConfiguration(f"https://{mon_host}:8443")
    ceph_cfg.verify_ssl = False
    apiclient = CephApiClient(ceph_cfg)

    token_api = cephauth.AuthApi(api_client=apiclient)
    try:
        res = token_api.api_auth_post(
            auth_request={"username": username, "password": password}, _request_timeout=5)
        apiclient.configuration.access_token = res.token
    except Exception as e:
        LOG.error(f"Failed to log in to the Ceph cluster, error: {e}")
        raise

    # Cache client with timestamp
    with _ceph_client_lock:
        _ceph_client_pool[mon_host] = (apiclient, now)

    return apiclient


def get_dpuagentclient(mv200_server, username="admin", password="yunsilicon"):
    """
    Return a DpuagentApiClient with valid token.
    Automatically re-login if token is expired.
    """
    now = time.time()
    with _dpuagent_client_lock:
        cached = _dpuagent_client_pool.get(mv200_server)
        if cached:
            client, acquired_time = cached
            if now - acquired_time < TOKEN_EXPIRE_SECONDS:
                return client  # token still valid

    # Need to login and get a new token
    dpuagent_cfg = DpuConfiguration(f"http://{mv200_server}:8000")
    dpuagent_cfg.verify_ssl = False
    apiclient = DpuApiClient(dpuagent_cfg)

    # --- disable urllib3 retry globally ---
    if hasattr(apiclient.rest_client, "pool_manager"):
        pool = apiclient.rest_client.pool_manager
        if hasattr(pool, "connection_pool_kw"):
            pool.connection_pool_kw["retries"] = Retry(
                total=0,       # no retries at all
                connect=False,
                read=False,
                redirect=False,
                status=False
            )
            pool.connection_pool_kw["timeout"] = Timeout(connect=2, read=2)

    token_api = dpuagentauth.AuthApi(api_client=apiclient)
    try:
        res = token_api.login_for_access_token_token_post(
            username=username, password=password, _request_timeout=2)
        apiclient.configuration.access_token = res.access_token
    except Exception as e:
        LOG.error(f"Failed to log in to the dpuagent {mv200_server}, error: {e}")
        raise

    # Cache client with timestamp
    with _dpuagent_client_lock:
        _dpuagent_client_pool[mv200_server] = (apiclient, now)

    return apiclient
