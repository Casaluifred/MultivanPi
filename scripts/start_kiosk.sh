#!/bin/bash
export DISPLAY=:0
export XAUTHORITY=/home/fred/.Xauthority
PROJECT_DIR="/home/fred/MultivanPi"
sudo fuser -k 3000/tcp > /dev/null 2>&1
sudo $PROJECT_DIR/venv/bin/python3 $PROJECT_DIR/backend/victron_service.py &
sleep 5
chromium-browser --kiosk --incognito --noerrdialogs --disable-infobars --window-size=1440,2560 "http://127.0.0.1:3000" &
