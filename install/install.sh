#!/bin/bash
set -e



filename=$(find . -maxdepth 1 -type f -name "*.whl" -printf "%f\n")
echo "=== 1. install brain python package ==="
if ! command -v pip3 >/dev/null 2>&1; then
    echo "Error: pip3 is NOT installed. Please install pip3 and try again." >&2
    exit 1
fi

pip3 install $filename

echo "=== 2. install brain-server service ==="
\cp -f brain-server.service /usr/lib/systemd/system/

echo "=== 3. enable  barin-server service auto start"
systemctl enable brain-server

systemctl restart brain-server

echo "=== install brain-server completed ==="


if ! command -v node &> /dev/null; then
    echo "install Node.js..."
    mkdir -p /usr/local/node
    tar -xJf node-v20.19.5-linux-x64.tar.xz -C /usr/local/node --strip-components=1

    export PATH=/usr/local/node/bin:$PATH
    echo 'export PATH=/usr/local/node/bin:$PATH' >> ~/.bashrc
fi

