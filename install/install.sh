#!/bin/bash
set -e



filename=$(find . -maxdepth 1 -type f -name "*.whl" -printf "%f\n")
echo "=== 1. install brain python package ==="
if ! command -v pip3 >/dev/null 2>&1; then
    echo "Error: pip3 is NOT installed. Please install pip3 and try again." >&2
    exit 1
fi

pip3 install $filename

echo "=== 2. install brain service ==="
\cp -f brain.service /usr/lib/systemd/system/

echo "=== 3. enable service auto start"
systemctl enable brain

systemctl restart brain

echo "=== install completed ==="


