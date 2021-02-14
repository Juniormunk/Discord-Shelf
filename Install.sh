#!/usr/bin/env bash
#bash <(curl -L https://github.com/resin-io/resin-wifi-connect/raw/master/scripts/raspbian-install.sh) -- -y

cd /home/pi/

apt install python3-pip
pip3 install discord
pip3 install asyncio
pip3 install json
pip3 install board
pip3 install rpi_ws281x adafruit-circuitpython-neopixel
pip3 install adafruit-ads1x15

wget -O WIFIScript.sh https://raw.githubusercontent.com/Juniormunk/Discord-Shelf/main/WIFIScript.sh

chmod +x /home/pi/WIFIScript.sh

lines="*/5 * * * * /home/pi/WIFIScript.sh"
( crontab -u pi -l; echo "$lines" ) | crontab -u pi -

lines="@reboot /home/pi/WIFIScript.sh" 
( crontab -u pi -l; echo "$lines" ) | crontab -u pi -

wget -O Shelf.py https://raw.githubusercontent.com/Juniormunk/Discord-Shelf/main/Shelf.py


printf "[Unit]
Description=Discord Shelf

[Service]
Type=simple
Restart=always
RestartSec=1
WorkingDirectory=/home/pi
User=root
Group=root
ExecStart=python3 /home/pi/Shelf.py

[Install]
WantedBy=multi-user.target" > /etc/systemd/system/discordshelf.service

systemctl enable discordshelf
