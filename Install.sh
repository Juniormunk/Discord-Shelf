#!/usr/bin/env bash
#bash <(curl -L https://github.com/resin-io/resin-wifi-connect/raw/master/scripts/raspbian-install.sh) -- -y


printf "#!/usr/bin/env bash

# export DBUS_SYSTEM_BUS_ADDRESS=unix:path=/host/run/dbus/system_bus_socket
# ^^^ this can cause barfing and isn't needed

# Choose a condition for running WiFi Connect according to your use case:

# 1. Is there a default gateway?
# ip route | grep default

# 2. Is there Internet connectivity?
# nmcli -t g | grep full

# 3. Is there Internet connectivity via a google ping?
wget --spider http://google.com 2>&1

# 4. Is there an active WiFi connection?
#iwgetid -r

if [ $? -eq 0 ]; then
    printf 'Skipping WiFi Connect\n'
else
    printf 'Starting WiFi Connect\n'
	var_id = cat /proc/cpuinfo | grep Serial | cut -d ' ' -f 2
    wifi-connect --portal-ssid "Discord_Shelf_%var_id"

fi

# Start your application here." >> /home/pi/WIFIScript.sh

chmod +x /home/pi/WIFIScript.sh

lines="*/5 * * * * ./home/pi/WIFIScript.sh\n @reboot ./home/pi/WIFIScript.sh" 
( crontab -u pi -l; echo "$lines" ) | crontab -u pi -

cd /home/pi/
wget -O Shelf.py https://raw.githubusercontent.com/Juniormunk/Discord-Shelf/main/Shelf.py


printf "[Unit]
Description=Discord Shelf
After=network.target
StartLimitIntervalSec=0
[Service]
Type=simple
Restart=always
RestartSec=1
User=root
Group=root
ExecStart=python3 /home/pi/Shelf.py

[Install]
WantedBy=multi-user.target" >> /etc/systemd/system/discordshelf.service

systemctl enable discordshelf

reboot
