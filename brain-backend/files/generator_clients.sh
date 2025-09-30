#!/bin/bash
# Copyright (C) 2021 - 2025, Shanghai Yunsilicon Technology Co., Ltd.
# All rights reserved.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

bash ${SCRIPT_DIR}/codegen.sh brain/clients ceph api-ref/ceph_openapi.yaml
bash ${SCRIPT_DIR}/codegen.sh brain/clients dpuagent api-ref/dpuagent_openapi.json
