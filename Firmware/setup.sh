#!/bin/bash
set -e

echo "DashCam setup"

sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-pillow ffmpeg fonts-dejavu python3-serial
pip3 install pytz pynmea2 st7789 picamera2 opencv-python-headless --break-system-packages
sudo raspi-config nonint do_spi 0
sudo raspi-config nonint do_camera 0
sudo raspi-config nonint do_serial_hw 0
sudo raspi-config nonint do_serial_cons 1
mkdir -p /home/pi/dashcam/{chunks,hours,videos,temp}
sudo bash -c 'cat > /etc/systemd/system/dashcam.service << EOF
[Unit]
Description=Dashcam
After=multi-user.target

[Service]
ExecStart=/usr/bin/python3 /home/pi/main.py
WorkingDirectory=/home/pi
Restart=always
User=pi

[Install]
WantedBy=multi-user.target
EOF'

sudo systemctl enable dashcam
sudo systemctl start dashcam

echo "Done rebooting"
sudo reboot
