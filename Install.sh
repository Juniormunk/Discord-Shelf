#!/usr/bin/env bash

if [ "$(id -u)" != 0 ]; then
  echo 'Sorry, you need to run this script with sudo'
  exit 1
fi

echo '>>> Enable I2C'
if grep -q 'i2c-bcm2708' /etc/modules; then
  echo 'Seems i2c-bcm2708 module already exists, skip this step.'
else
  echo 'i2c-bcm2708' >> /etc/modules
fi
if grep -q 'i2c-dev' /etc/modules; then
  echo 'Seems i2c-dev module already exists, skip this step.'
else
  echo 'i2c-dev' >> /etc/modules
fi
if grep -q 'dtparam=i2c1=on' /boot/config.txt; then
  echo 'Seems i2c1 parameter already set, skip this step.'
else
  echo 'dtparam=i2c1=on' >> /boot/config.txt
fi
if grep -q 'dtparam=i2c_arm=on' /boot/config.txt; then
  echo 'Seems i2c_arm parameter already set, skip this step.'
else
  echo 'dtparam=i2c_arm=on' >> /boot/config.txt
fi
if [ -f /etc/modprobe.d/raspi-blacklist.conf ]; then
  sed -i 's/^blacklist spi-bcm2708/#blacklist spi-bcm2708/' /etc/modprobe.d/raspi-blacklist.conf
  sed -i 's/^blacklist i2c-bcm2708/#blacklist i2c-bcm2708/' /etc/modprobe.d/raspi-blacklist.conf
else
  echo 'File raspi-blacklist.conf does not exist, skip this step.'
fi
bash <(curl -L https://github.com/resin-io/resin-wifi-connect/raw/master/scripts/raspbian-install.sh) -- -y

cd /home/pi/

apt -y install python3-pip
pip3 install discord
pip3 install asyncio
pip3 install board
pip3 install rpi_ws281x adafruit-circuitpython-neopixel
pip3 install adafruit-ads1x15
pip3 install schedule


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
