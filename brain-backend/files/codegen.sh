#!/bin/bash
# Copyright (C) 2021 - 2025, Shanghai Yunsilicon Technology Co., Ltd.
# All rights reserved.

set -exo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
JAVA_EXEC_PATH="/usr/bin/java"

CODEGEN_CLI_NAME="openapi-generator-cli"
# specify client version if necessary
CODEGEN_CLI_VERSION="7.0.1"
CODEGEN_CLI_SUFFIX="jar"
CODEGEN_CLI_EXEC_DIR="/tmp/codegen"
CODEGEN_CLI_OUTPUT_DIR="generated"


CODEGEN_CLI_TAR_RAW_NAME="${CODEGEN_CLI_NAME}-${CODEGEN_CLI_VERSION}.${CODEGEN_CLI_SUFFIX}"
CODEGEN_CLI_TAR_NAME="${CODEGEN_CLI_NAME}.${CODEGEN_CLI_SUFFIX}"
CODEGEN_CLI_TAR_FILE="${CODEGEN_CLI_EXEC_DIR}/${CODEGEN_CLI_TAR_NAME}"
CODEGEN_CLI_OUTPUT_PATH="${CODEGEN_CLI_EXEC_DIR}/${CODEGEN_CLI_OUTPUT_DIR}"
# specify root dir of generated python package if necessary
CLIENT_ROOT_DIR=$1
CLIENT_PACKAGE_NAME=$2
CLIENT_DIR="${CLIENT_ROOT_DIR}/${CLIENT_PACKAGE_NAME}"
CLIENT_SOURCE_DIR="${CODEGEN_CLI_OUTPUT_PATH}/${CLIENT_DIR}"
CLIENT_PACKAGE_NAME_FULL=$(echo ${CLIENT_DIR} | sed "s/\//./g")
CLIENT_OPENAPI_FILE_PATH=$3

cd "$(dirname ${BASH_SOURCE})/.."

echo "Pre-generate checking"
# pre-generate checking
if [[ ! -d ${CLIENT_ROOT_DIR} ]]; then
    echo "ROOT dir ${CLIENT_ROOT_DIR} for code generation does not exist."
    mkdir -p ${CLIENT_ROOT_DIR}
fi

if [[ ! -f ${CLIENT_OPENAPI_FILE_PATH} ]]; then
    echo "File ${CLIENT_OPENAPI_FILE_PATH} does not exist."
    exit 1
fi

echo "Guarantee essential tools"
if [[ ! -f ${JAVA_EXEC_PATH} ]]; then
    echo "Command java does not exist. Installing it."
    if [ -f /etc/os-release ]; then
        if grep -qi "centos" /etc/os-release; then
            install_cmd="yum"
        elif grep -qi "ubuntu" /etc/os-release; then
            echo "Detected Ubuntu"
            install_cmd="apt"
        else
            echo "Unknown Linux Distribution"
            exit 1
        fi
    fi
    ${install_cmd} install -y default-jdk > /dev/null
fi
java -version > /dev/null



echo "Preparing working directory"
mkdir -p ${CODEGEN_CLI_EXEC_DIR}
rm -rf ${CODEGEN_CLI_OUTPUT_PATH}
mkdir -p ${CODEGEN_CLI_OUTPUT_PATH}
 
echo "installing codegen client if needed"
if [[ ! -f ${CODEGEN_CLI_TAR_FILE} ]]; then
    cp ${SCRIPT_DIR}/${CODEGEN_CLI_TAR_RAW_NAME} ${CODEGEN_CLI_TAR_FILE}
    chmod 755 ${CODEGEN_CLI_TAR_FILE}
fi

echo "Do generating stuff"
java -jar ${CODEGEN_CLI_TAR_FILE} generate -i ${CLIENT_OPENAPI_FILE_PATH} -g python -o ${CODEGEN_CLI_OUTPUT_PATH} --package-name ${CLIENT_PACKAGE_NAME_FULL} > /dev/null

echo "Adding copyright headers"
find ${CLIENT_SOURCE_DIR} -name \*.py | xargs -i sed -i "1i\# Copyright (C) 2021 - 2025, Shanghai Yunsilicon Technology Co., Ltd.\n" {} > /dev/null

echo "Copying generated code to project"
rm -rf ${CLIENT_DIR}
cp -rf ${CLIENT_SOURCE_DIR} ${CLIENT_DIR}

echo "Conguratulations :)"
