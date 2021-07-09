import asyncio
import json
import logging
import multiprocessing
import os
import sys
import threading
import time
from datetime import datetime
from datetime import time as datetime_time
from datetime import timedelta
from enum import Enum
from queue import Queue

import Adafruit_ADS1x15
import board
import discord
import neopixel
import NetworkManager
import schedule
from discord.utils import get
from flask import Flask, render_template, request

global pixels
global friends
intents = discord.Intents.all()
client = discord.Client(intents=intents)
config = None
lastBotToken = ""
lastGuildID = 0
global slots
friends = []
configPath = "/boot/shelf_config.json"
logPath = "/boot/latest.log"

app = Flask(__name__)


class LightStatus(Enum):
    Loading = 1
    JSONError = 2
    Loaded = 3
    WIFIError = 4
    GuildError = 5


def checkInternet(url='8.8.8.8'):
    response = os.system("ping -c 1 " + url)
    # and then check the response...
    if response == 0:
        pingstatus = True
    else:
        pingstatus = False

    return pingstatus


def verifyConfig():
    didAdd = False
    if(not("Discord Bot Token" in config)):
        config["Discord Bot Token"] = ""
        didAdd = True

    if(not("Slots" in config)):
        config["Slots"] = [[0, 1, 2], [3, 4, 5], [6, 7, 8], [9, 10, 11],
                           [12, 13, 14], [15, 16, 17], [18, 19, 20], [21, 22, 23]]
        didAdd = True

    if(not("Night Mode Start Time" in config)):
        config["Night Mode Start Time"] = "22:00:00"
        didAdd = True

    if(not("Night Mode Start Off Time" in config)):
        config["Night Mode Start Off Time"] = "22:05:00"
        didAdd = True

    if(not("Night Mode End Off Time" in config)):
        config["Night Mode End Off Time"] = "06:00:00"
        didAdd = True

    if(not("Night Mode End Time" in config)):
        config["Night Mode End Time"] = "06:05:00"
        didAdd = True

    if(not("Use Night Mode" in config)):
        config["Use Night Mode"] = False
        didAdd = True

    if(not("Fade Speed" in config)):
        config["Fade Speed"] = 0.01
        didAdd = True

    if(didAdd == True):
        logging.error(
            "Config did not contain necessary objects adding defaults.")
    saveConfig()


def openConfig():
    global config
    global lightStatus
    try:
        with open(configPath, 'r') as infile:
            config = json.loads(infile.read())
            infile.close()
            verifyConfig()
    except json.decoder.JSONDecodeError as e:
        logging.error(e)
        logging.error("Could not parsing json file!")
        lightStatus = LightStatus.JSONError


def getClient():
    return client


def getConfigBotToken():
    return config["Discord Bot Token"]


def getConfigGuildID():
    return config["Guild ID"]


def getGuild():
    return getClient().get_guild(getConfigGuildID())


def getConfigUserID(index):
    return config["Users"][index]["ID"]


def getConfigSlots():
    try:
        return config["Slots"]
    except:
        return [[0, 1, 2], [3, 4, 5]]


def getConfigUserName(index):
    return str(config["Users"][index]["Name"])


def getConfigUserSlot(index):
    return int(config["Users"][index]["Slot"])


def getConfigUserMobileStatus(index):
    return config["Users"][index]["ShowMobileStatus"]


def getConfigUserFavoriteGames(index):
    return config["Users"][index]["FavoriteGames"]


def setConfigUserName(index, name):
    config["Users"][index]["Name"] = str(name)
    saveConfig()


def setConfigUserID(index, ID):
    config["Users"][index]["ID"] = ID
    saveConfig()


def getGuildMember(id):
    return getGuild().get_member(id)


def getGuildMembers():
    return getGuild().members


def getConfigNightModeStartTime():
    return config["Night Mode Start Time"]


def getConfigNightModeStartOffTime():
    return config["Night Mode Start Off Time"]


def getConfigNightModeEndOffTime():
    return config["Night Mode End Off Time"]


def getConfigNightModeEndTime():
    return config["Night Mode End Time"]


def getConfigUseNightMode():
    try:
        return config["Use Night Mode"]
    except:
        return False


def getConfigFadeSpeed():
    return config["Fade Speed"]


def saveConfig():
    with open(configPath, 'w') as outfile:
        json.dump(config, outfile, indent=2)
        outfile.flush()
        os.fsync(outfile.fileno())
        outfile.close()


class Friend():
    class Status(Enum):
        Online = 1
        Ingame = 2
        Offline = 3
        Away = 4
        Dnd = 5
        IDError = 6
        Favgame = 7

    def __init__(self, name_, id_, slot_, mobileStatus_, favoriteGames_, member_, index_):
        self._name = name_
        self.index = index_
        self.member = member_
        self._id = id_
        self.slot = slot_
        self.mobileStatus = mobileStatus_
        self.favoriteGames = favoriteGames_
        self.status = self.Status.Offline

    def setID(self, id):
        self._id = id
        setConfigUserID(self.index, id)
        saveConfig()

    def getID(self):
        return self._id

    def setName(self, name):
        self._name = name
        setConfigUserName(self.index, name)
        saveConfig()

    def getName(self):
        return self._name

    def isFavGame(self, game):
        if game.upper() in (name.upper() for name in self.favoriteGames):
            return True
        else:
            return False


def time_diff(start, end):
    if isinstance(start, datetime_time):  # convert to datetime
        assert isinstance(end, datetime_time)
        start, end = [datetime.combine(datetime.min, t) for t in [start, end]]
    if start <= end:  # e.g., 10:33:26-11:15:49
        return end - start
    else:  # end < start e.g., 23:55:00-00:25:00
        end += timedelta(1)  # +day
        assert end > start
        return end - start


def is_time_between(begin_time, end_time, check_time=None):
    # If check time is not given, default to current UTC time
    check_time = check_time or datetime.utcnow().time()
    if begin_time < end_time:
        return check_time >= begin_time and check_time <= end_time
    else:  # crosses midnight
        return check_time >= begin_time or check_time <= end_time


def lightThread():
    global lightStatus
    adc = Adafruit_ADS1x15.ADS1115()
    mod_brightness = .5
    direction = -1

    try:
        step = getConfigFadeSpeed()
    except Exception as e:
        logging.error(e)
        step = .08

    while True:
        try:
            step = getConfigFadeSpeed()
        except:
            pass

        try:
            brightness = (adc.read_adc(0, gain=1)-26352)/-26352.0
        except:
            brightness = 1

        if brightness < .05:
            brightness = 0
        if brightness > .95:
            brightness = 1

        mod_brightness += step*direction
        if(mod_brightness > (1-(step*2)) and direction > 0):
            direction = -1

        if(mod_brightness < ((step*2)) and direction < 0):
            direction = 1

        slots_updated = []
        updated_all = False

        if(lightStatus == LightStatus.WIFIError):
            updated_all = True
            pixels[0] = [255*brightness*mod_brightness,
                         0, 255*brightness*mod_brightness]
            for slot in slots:
                for i in slot:
                    pixels[i] = [255*brightness*mod_brightness,
                                 0, 255*brightness*mod_brightness]
        else:

            if(lightStatus == LightStatus.Loaded):

                brightnesstimemodifier = 1.0

                if(getConfigUseNightMode()):
                    current = datetime.strptime(
                        datetime.now().strftime("%H:%M:%S"), '%H:%M:%S')

                    start = datetime.strptime(
                        getConfigNightModeStartTime(), '%H:%M:%S')
                    startoff = datetime.strptime(
                        getConfigNightModeStartOffTime(), '%H:%M:%S')
                    endoff = datetime.strptime(
                        getConfigNightModeEndOffTime(), '%H:%M:%S')
                    end = datetime.strptime(
                        getConfigNightModeEndTime(), '%H:%M:%S')

                    startTimeDiff = time_diff(start, startoff)
                    endTimeDiff = time_diff(endoff, end)

                    startTimeDiffSec = startTimeDiff.seconds
                    endTimeDiffSec = endTimeDiff.seconds

                    if(not(startTimeDiffSec == 0) and is_time_between(start, startoff, current)):
                        brightnesstimemodifier = 1 - \
                            (1.0/startTimeDiffSec)*(current-start).seconds

                    if(is_time_between(startoff, endoff, current)):
                        brightnesstimemodifier = 0

                    if(not(endTimeDiffSec == 0) and is_time_between(endoff, end, current)):
                        brightnesstimemodifier = (
                            1.0/endTimeDiffSec)*(current-endoff).seconds
                for friend in friends:
                    if((friend.slot >= 0) and friend.slot < len(slots)):
                        for i in slots[friend.slot]:
                            slots_updated.append(friend.slot)
                            if(friend.status == friend.Status.Online):
                                pixels[i] = [0, 0, 255*brightness*brightnesstimemodifier]
                            if(friend.status == friend.Status.Offline):
                                pixels[i] = [0, 0, 0]
                            if(friend.status == friend.Status.Away):
                                pixels[i] = [255*brightness*brightnesstimemodifier, 255*brightness*brightnesstimemodifier, 0]
                            if(friend.status == friend.Status.Favgame):
                                pixels[i] = [
                                    0, 255*brightness*mod_brightness*brightnesstimemodifier, 0]
                            if(friend.status == friend.Status.Ingame):
                                pixels[i] = [0, 255*brightness*brightnesstimemodifier, 0]
                            if(friend.status == friend.Status.Dnd):
                                pixels[i] = [60*brightness*brightnesstimemodifier, 0, 0]
                            if(friend.status == friend.Status.IDError):
                                pixels[i] = [255*brightness*brightnesstimemodifier, 0, 255*brightness]

            if(lightStatus == LightStatus.Loading):
                updated_all = True
                for slot in slots:
                    for i in slot:
                        pixels[i] = [0, 0, 255*brightness*mod_brightness]
                pixels[0] = [0, 0, 255*brightness*mod_brightness]
            if(lightStatus == LightStatus.JSONError):
                updated_all = True
                for slot in slots:
                    for i in slot:
                        pixels[i] = [255*brightness*mod_brightness, 0, 0]
                pixels[0] = [255*brightness*mod_brightness, 0, 0]
            if(lightStatus == LightStatus.GuildError):
                updated_all = True
                for slot in slots:
                    for i in slot:
                        pixels[i] = [255*brightness*mod_brightness, 255 *
                                     brightness*mod_brightness, 255*brightness*mod_brightness]
        if not updated_all:
            for i in range(len(slots)):
                if i not in slots_updated:
                    for x in slots[i]:
                        pixels[x] = [0, 0, 0]
        time.sleep(.01)


@app.route('/', methods=['POST', 'GET'])
def homePage():
    global config
    global lastBotToken
    global lastGuildID
    try:

        output = ""
        output += "<html>"
        output += "<head>"
        output += '''<link rel="icon" type="image/svg+xml" href="http://discord.com/assets/41484d92c876f76b20c7f746221e8151.svg">'''
        output += "<title>Discord Shelf</title>"
        output += '''<style type="text/css">
                            #container {
                            width:70%;
                            height:80%;
                            padding:5px 7px 5px 5px;
                            }
                            #txtarea {
                            font-size:16;
                            resize:none;
                            display:block;
                            background: #23272A;
                            width:99%;
                            height:99%;
                            padding:0.5%;
                            margin:0;
                            overflow-y: scroll;
                            overflow-x: scroll;
                                color: #FFFFFF;
                            }
                            .button {
                              background-color: #4CAF50; /* Green */
                              border: none;
                              color: white;
                              padding: 15px 32px;
                              text-align: center;
                              text-decoration: none;
                              display: inline-block;
                              font-size: 16px;
                              margin: 4px 2px;
                              cursor: pointer;
                            }
                            .button4 {background-color: #e7e7e7; color: black;} /* Gray */
                            </style>'''
        output += "</head>"
        output += "<center>"
        output += '''<body style="background-color:#23272A;">'''
        output += '''<h1 style="color:#7289DA;">Welcome to the discord shelf configuration editor. Below you will find a json file that will allow you to configure your shelf.</h1>'''
        output += '''<div id="container">'''
        if request.method == 'GET':
            with open(configPath, 'r') as infile:
                file = infile.read()
                infile.close()
            output += '''<form method='POST' enctype='multipart/form-data' action='/'>
                        <textarea id="txtarea" name="json">'''+file+'''</textarea>
                        <br>
                        <br>
                        <br>
                        <br>
                        <input class="button button4" type="submit" value="Apply" name="submit">
                        </form>'''

        if request.method == 'POST':
            if request.form.get('reboot'):
                output += '''<h1 style="color:RED;">Rebooting...</h1>'''
                os.system('sudo reboot')
            if not(request.form.get('reboot')):
                try:
                    print(config)
                    config = json.loads(request.form["json"])

                    saveConfig()

                    with open(configPath, 'r') as infile:
                        file = infile.read()
                        infile.close()
                    output += '''<h1 style="color:RED;">Reboot is required to apply any changes.</h1>'''
                    output += '''<form method='POST' enctype='multipart/form-data' action='/'>
                            <input class="button button4" type="submit" value="Reboot" name="reboot">
                            </form>'''
                    output += '''<form method='POST' enctype='multipart/form-data' action='/'>
                            <textarea id="txtarea" name="json">'''+file+'''</textarea>
                            <br>
                            <br>
                            <br>
                            <br>
                            <input class="button button4" type="submit" value="Apply" name="submit">
                            </form>'''
                except Exception as e:
                    logging.error(e)
                    with open(configPath, 'r') as infile:
                        file = infile.read()
                        infile.close()
                    config = json.loads(file)
                    saveConfig()
                    output += '''<h1 style="color:RED;">Error parsing json file</h1>'''
                    output += '''<form method='POST' enctype='multipart/form-data' action='/'>
                            <textarea id="txtarea" name="json">'''+request.form["json"]+'''</textarea>
                            <br>
                            <br>
                            <br>
                            <br>
                            <input class="button button4" type="submit" value="Apply" name="submit">
                            </form>'''
        output += '''</div>'''
        output += "</center>"
        output += "</body>"
        output += "</html>"
        return output
    except Exception as e:
        logging.error(e)
        output = ""
        output += "<html>"
        output += "<head>"
        output += '''<link rel="icon" type="image/svg+xml" href="http://discord.com/assets/41484d92c876f76b20c7f746221e8151.svg">'''
        output += "<title>Discord Shelf</title>"
        output += '''<style>
.center {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 200px;
}
</style>'''
        output += "</head>"
        output += "<center>"
        output += '''<body style="background-color:#23272A;">'''
        output += '''<div id="container">'''
        output += '''<h1 style="color:RED;">An error has occured please restart. If this error continues please contact the developer.</h1>'''
        '''<form action='/logs'>
                        <br>
                        <br>
                        <br>
                        <br>
                        <input class="button button4" type="logs" value="View Logs">
                        </form>'''
        output += '''</div>'''
        output += "</center>"
        output += "</body>"
        output += "</html>"
        return output


@app.route('/log')
def logPage():
    log = "Error finding log file... please contact developer"
    with open(logPath, 'r') as infile:
        log = infile.read()
        infile.close()
    return log


def serverThread():
    app.run(host='0.0.0.0', port=80)


def updateUsernames():
    for friend in friends:
        if(friend.member != None):
            if(friend.member.name != friend.getName()):
                friend.setName(friend.member.name)


def updateFriendStatus():
    global lightStatus
    lightStatus = LightStatus.Loaded
    for friend in friends:
        if(friend.member != None):
            if((friend.member.is_on_mobile()) and (friend.mobileStatus == False)):
                continue
            if(friend.member.status == discord.Status.online):
                friend.status = friend.Status.Online
            if(friend.member.status == discord.Status.idle):
                friend.status = friend.Status.Away
            if(friend.member.status == discord.Status.dnd):
                friend.status = friend.Status.Dnd
            if(friend.member.status == discord.Status.dnd):
                friend.status = friend.Status.Dnd
            if(friend.member.status == discord.Status.offline):
                friend.status = friend.Status.Offline
            if friend.member.activity != None:
                if friend.member.activity.type == discord.ActivityType.playing:
                    friend.status = friend.Status.Ingame
                    if(friend.isFavGame(friend.member.activity.name)):
                        friend.status = friend.Status.Favgame
        else:
            friend.status = friend.Status.IDError


def checkInternetConnection():
    global lightStatus
    global y
    while(True):
        if(checkInternet() == False):
            time.sleep(5)
            if(checkInternet() == False):
                lightStatus = LightStatus.WIFIError
                if(y.is_alive()):
                    y.terminate()
        else:
            if(lightStatus==LightStatus.WIFIError):
                lightStatus = LightStatus.Loaded
            if(not(y.is_alive())):
                y = multiprocessing.Process(target=serverThread)
                y.start()
        time.sleep(30)


def loadConfig():
    friends.clear()
    for i in range(0, len(config["Users"])):
        friend = Friend(getConfigUserName(i), getConfigUserID(i), getConfigUserSlot(
            i), getConfigUserMobileStatus(i), getConfigUserFavoriteGames(i), None, i)
        friends.append(friend)
    for friend in friends:
        if((int(friend.getID()) == -1) or (int(friend.getID()) == 0)):
            name = friend.getName()
            member = None
            for mem in getGuildMembers():
                if(mem.name == name):
                    if(member != None):
                        # Add light error code
                        logging.error(
                            'Found multiple players with that name: {0}'.format(name))
                        continue
                    member = mem
            if(member == None):
                # Add light error code
                logging.error(
                    "Could not find player with name: {0}".format(name))
                continue
            friend.setID(int(member.id))

    for mem in getGuildMembers():
        for friend in friends:
            if(friend.getID() == int(mem.id)):
                friend.member = mem


@client.event
async def on_ready():
    global lightStatus
    logging.info('We have logged in as {0.user}'.format(getClient()))
    if((getGuild() == None) or (getGuildMembers() == None)):
        lightStatus = LightStatus.GuildError
        while(True):
            time.sleep(1)
    loadConfig()
    updateUsernames()
    updateFriendStatus()

    logging.info('Connected to server {0} aka {1}'.format(
        getConfigGuildID(), getGuild().name))

    schedule.every(120).seconds.do(updateFriendStatus)
    schedule.every(20).minutes.do(updateUsernames)

    lightStatus = LightStatus.Loaded

    while True:
        schedule.run_pending()
        await asyncio.sleep(1)


@client.event
async def on_member_update(before, after):
    updateFriendStatus()

if __name__ == '__main__':
    os.system('sudo hostnamectl set-hostname discordshelf')

    if os.path.exists(logPath):
        os.remove(logPath)

    logging.basicConfig(filename=logPath, level=logging.ERROR)

    global lightStatus
    lightStatus = LightStatus.Loading
    pixels = neopixel.NeoPixel(board.D18, 30)
    if not os.path.exists(configPath):
        with open(configPath, 'w') as file:
            file.write('''{
      "Discord Bot Token": "",
      "Fade Speed": 0.01,
      "Slots": [[0,1,2],[3,4,5],[6,7,8],[9,10,11],[12,13,14],[15,16,17],[18,19,20],[21,22,23]],
      "Guild ID": 0,
      "Users": [
        {
          "Name": "",
          "ID": -1,
          "Slot": -1,
          "ShowMobileStatus": false,
          "FavoriteGames": [
            "",
            "",
            ""
          ]
        },
        {
          "Name": "",
          "ID": -1,
          "Slot": -1,
          "ShowMobileStatus": false,
          "FavoriteGames": [
            "",
            "",
            ""
          ]
        },
        {
          "Name": "",
          "ID": -1,
          "Slot": -1,
          "ShowMobileStatus": false,
          "FavoriteGames": [
            "",
            "",
            ""
          ]
        }
      ]
    }''')
            file.close()
    rewriteConfig = False
    with open(configPath, 'r') as file:
        if(file.read() == ""):
            rewriteConfig = True
            file.close()
    if(rewriteConfig):
        with open(configPath, 'w') as file:
            file.write('''{
            "Discord Bot Token": "",
            "Fade Speed": 0.01,
            "Slots": [[0,1,2],[3,4,5],[6,7,8],[9,10,11],[12,13,14],[15,16,17],[18,19,20],[21,22,23]],
            "Guild ID": 0,
            "Users": [
                {
                "Name": "",
                "ID": -1,
                "Slot": -1,
                "ShowMobileStatus": false,
                "FavoriteGames": [
                    "",
                    "",
                    ""
                ]
                },
                {
                "Name": "",
                "ID": -1,
                "Slot": -1,
                "ShowMobileStatus": false,
                "FavoriteGames": [
                    "",
                    "",
                    ""
                ]
                },
                {
                "Name": "",
                "ID": -1,
                "Slot": -1,
                "ShowMobileStatus": false,
                "FavoriteGames": [
                    "",
                    "",
                    ""
                ]
                }
            ]
            }''')
            file.close()
    openConfig()
    slots = getConfigSlots()
    if (lightStatus != LightStatus.JSONError):
        lightStatus = LightStatus.Loading

    x = threading.Thread(target=lightThread)
    x.setDaemon(True)
    x.start()

    count = 0
    while(checkInternet() == False):
        time.sleep(1)
        count = count+1
        if(count >= 2):
            lightStatus = LightStatus.WIFIError

    y = multiprocessing.Process(target=serverThread)
    y.daemon = True
    y.start()

    lightStatus = LightStatus.Loading

    z = threading.Thread(target=checkInternetConnection)
    z.setDaemon(True)
    z.start()

    if (getConfigBotToken() == "" or getConfigBotToken() == 0):
        lightStatus = LightStatus.JSONError
        while True:
            time.sleep(1)

    getClient().run(getConfigBotToken())
