```bash
# on raspi
curl https://get.pimoroni.com/scrollphathd | bash

# deploy
scp raspi_stationboard.py pi@192.168.0.102:stationboard

crontab -e
# @reboot /home/pi/stationboard/raspi_stationboard.py
```
