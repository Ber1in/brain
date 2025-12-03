#!/bin/bash
set -e

echo "=== Brain Installation Script Start ==="

############################################
# 0. Locate wheel package
############################################
filename=$(find . -maxdepth 1 -type f -name "*.whl" -printf "%f\n")
if [[ -z "$filename" ]]; then
    echo "Error: No .whl package found in current directory."
    exit 1
fi
echo "Found wheel package: $filename"

############################################
# 1. Ensure pip configuration (~/.pip/pip.conf)
############################################
echo "=== 1. Configure pip mirror ==="
mkdir -p ~/.pip

PIP_CONF_PATH=~/.pip/pip.conf

cat > "$PIP_CONF_PATH" <<EOF
[global]
index-url = http://mirrors.yunsilicon.com/pypi/simple/

[install]
trusted-host=mirrors.yunsilicon.com
EOF

echo "pip mirror configured at $PIP_CONF_PATH"

############################################
# 2. Install brain pip package
############################################
echo "=== 2. Installing brain python package ==="
if ! command -v pip3 >/dev/null 2>&1; then
    echo "Error: pip3 is NOT installed. Please install pip3 and try again." >&2
    exit 1
fi

pip3 install "$filename"
echo "Brain package installed."

############################################
# 3. Install systemd service
############################################
echo "=== 3. Installing brain-server service ==="
\cp -f brain-server.service /usr/lib/systemd/system/

systemctl daemon-reload
systemctl enable brain-server
systemctl restart brain-server
echo "brain-server service installed & started."

############################################
# 4. Install Node.js if necessary
############################################
if ! command -v node &> /dev/null; then
    echo "=== 4. Node.js not found, installing Node.js... ==="
    mkdir -p /usr/local/node
    tar -xJf node-v20.19.5-linux-x64.tar.xz -C /usr/local/node --strip-components=1

    export PATH=/usr/local/node/bin:$PATH
    echo 'export PATH=/usr/local/node/bin:$PATH' >> ~/.bashrc
else
    echo "Node.js already installed."
fi

############################################
# 5. Set npm registry
############################################
echo "=== 5. Configure npm registry ==="
npm config set registry https://registry.npmmirror.com
echo "npm registry set to https://registry.npmmirror.com"

############################################
# 6. Extract node_modules.tar.gz to brain-frontend
############################################
echo "=== 6. Extracting node_modules.tar.gz to ../brain-frontend ==="

FRONTEND_DIR="../brain-frontend"
TARBALL="node_modules.tar.gz"

if [[ ! -d "$FRONTEND_DIR" ]]; then
    echo "Error: Frontend directory '$FRONTEND_DIR' does not exist."
    exit 1
fi

if [[ ! -f "$TARBALL" ]]; then
    echo "Error: $TARBALL not found in current directory."
    exit 1
fi

tar -xzf "$TARBALL" -C "$FRONTEND_DIR"
echo "node_modules extracted to $FRONTEND_DIR"

############################################
echo "=== Brain installation completed successfully ==="

