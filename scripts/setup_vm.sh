#!/usr/bin/env bash
# Provisions an Oracle Cloud Always Free ARM (Ampere A1) VM - Ubuntu 22.04/24.04.
# Target: 2-4 OCPU, 8-24 GB RAM. No GPU needed.
set -euo pipefail

sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv python3-pip ffmpeg \
    fonts-dejavu-core libass-dev build-essential sqlite3 git

# oracle images ship with restrictive iptables - open what postiz needs if you
# self-host it on this box, and mirror the rule in the OCI security list.

git clone <REPO_URL> ~/shitpost-factory || true
cd ~/shitpost-factory
make setup

# Create required directories
mkdir -p logs work output assets/fonts assets/music assets/sfx assets/backgrounds
for d in logs work output assets/fonts assets/music assets/sfx assets/backgrounds; do
    touch "$d/.gitkeep" 2>/dev/null || true
done

# cron every 8h. use flock so a slow render never overlaps the next run.
CRON='0 0,8,16 * * * /usr/bin/flock -n /tmp/factory.lock -c "cd ~/shitpost-factory && make cron >> logs/cron.log 2>&1"'
( crontab -l 2>/dev/null | grep -v shitpost-factory; echo "$CRON" ) | crontab -

echo "done. add credentials to .env, then: make check"
