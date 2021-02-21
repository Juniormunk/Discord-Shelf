import discord
import asyncio
import json
from discord.utils import get
import time
import logging
import os
import schedule
import sys
from enum import Enum
import threading
import board
import neopixel
import Adafruit_ADS1x15
import urllib.request
from flask import Flask,render_template,request



config = None
slots = None
app = Flask(__name__)


pixels = neopixel.NeoPixel(board.D18, 30)

if os.path.exists("/boot/latest.log"):
    os.remove("/boot/latest.log")
if not os.path.exists('/boot/shelf_config.json'):
    with open('/boot/shelf_config.json', 'w') as file:
        file.write('''{
  "Discord Bot Token": "",
  "Fade Speed": 0.01,
  "Slots": [[1,2,3],[4,5,6],[7,8,9],[10,11,12]],
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
        
logging.basicConfig(filename='/boot/latest.log',level=logging.ERROR)

        
def openConfig():
    global config
    global lightStatus
    try:
        with open('/boot/shelf_config.json', 'r') as infile:
            config = json.loads(infile.read())
            infile.close()
    except json.decoder.JSONDecodeError as e:
        logging.error(e)
        logging.error("Could not parsing json file!")
        lightStatus = LightStatus.JSONError
        x.start()
        while(True):
            time.sleep(1)
            
openConfig()


lastBotToken = ""
def getConfigBotToken():
    return config["Discord Bot Token"]
def getConfigGuildID():
    return config["Guild ID"]
def getGuild():
    return client.get_guild(getConfigGuildID())
def getConfigUserID(index):
    return config["Users"][index]["ID"]
def getConfigSlots():
    return config["Slots"]
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
def getConfigFadeSpeed():
    return config["Fade Speed"]
def saveConfig():
    with open('/boot/shelf_config.json', 'w') as outfile:
        json.dump(config, outfile, indent = 2)
        outfile.close()

@app.route('/', methods = ['POST', 'GET'])
def homePage():
    try:
        global config
            
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
            with open('/boot/shelf_config.json', 'r') as infile:
                    file = infile.read()
                    infile.close()
            output += '''<form method='POST' enctype='multipart/form-data' action='/'>
                        <textarea id="txtarea" name="json">'''+file+'''</textarea>
                        <br>
                        <br>
                        <br>
                        <br>
                        <input class="button button4" type="submit" value="Apply">
                        </form>'''
        if request.method == 'POST':
            try:
                config = json.loads(request.form["json"])
                saveConfig()
                with open('/boot/shelf_config.json', 'r') as infile:
                    file = infile.read()
                    infile.close()
                if lastBotToken != getConfigBotToken():
                   output+='''<h1 style="color:RED;">You must restart to apply some settings changed.</h1>'''
                if lastBotToken == getConfigBotToken():
                    loadConfig()
                    updateFriendStatus()
                
                output += '''<form method='POST' enctype='multipart/form-data' action='/'>
                        <textarea id="txtarea" name="json">'''+file+'''</textarea>
                        <br>
                        <br>
                        <br>
                        <br>
                        <input class="button button4" type="submit" value="Apply">
                        </form>'''
            except Exception as e:
                logging.error(e)
                with open('/boot/shelf_config.json', 'r') as infile:
                    file = infile.read()
                    infile.close()
                config = json.loads(file)
                saveConfig()
                loadConfig()
                updateFriendStatus()
                output+='''<h1 style="color:RED;">Error parsing json file</h1>'''
                output += '''<form method='POST' enctype='multipart/form-data' action='/'>
                        <textarea id="txtarea" name="json">'''+request.form["json"]+'''</textarea>
                        <br>
                        <br>
                        <br>
                        <br>
                        <input class="button button4" type="submit" value="Apply">
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
        output+='''<h1 style="color:RED;">An error has occured please restart. If this error continues please contact the developer.</h1>'''
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
    log="Error finding log file... please contact developer"
    with open('/boot/latest.log', 'r') as infile:
            log = infile.read()
            infile.close()
    return log
    
def serverThread():
    app.run(host='0.0.0.0', port=80)

y = threading.Thread(target=serverThread)

y.start()

class LightStatus(Enum):
    Loading = 1
    JSONError = 2
    Loaded = 3
    WIFIError = 4

lightStatus = LightStatus.Loading

class Friend():
    class Status(Enum):
        Online = 1
        Ingame = 2
        Offline = 3
        Away = 4
        Dnd = 5
        IDError=6
        Favgame = 7
    def __init__(self, name_, id_, slot_, mobileStatus_, favoriteGames_, member_,index_): 
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
 
friends = []

def lightThread():
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
            brightness = (adc.read_adc(0, gain=1)-26352)/-26352.0
        except:
            brightness = 1
        if brightness<.05:
            brightness = 0
        if brightness>.95:
            brightness = 1
            
        mod_brightness += step*direction
        if(mod_brightness>(1-(step*2)) and direction>0):
            direction=-1
            
        if(mod_brightness<((step*2)) and direction<0):
            direction=1

        slots_updated = []
            
        if(lightStatus == LightStatus.Loaded):
            for friend in friends:
                if((friend.slot>=0) and friend.slot<len(slots)):
                    for i in slots[friend.slot]:
                        slots_updated.append(friend.slot)
                        if(friend.status == friend.Status.Online):
                            pixels[i] = [0,0,255*brightness]
                        if(friend.status == friend.Status.Offline):
                            pixels[i] = [0,0,0]
                        if(friend.status == friend.Status.Away):
                            pixels[i] = [255*brightness,255*brightness,0]
                        if(friend.status == friend.Status.Favgame):
                            pixels[i] = [0,255*brightness*mod_brightness,0]
                        if(friend.status == friend.Status.Ingame):
                            pixels[i] = [0,255*brightness,0]
                        if(friend.status == friend.Status.Dnd):
                            pixels[i] = [60*brightness,0,0]
                        if(friend.status == friend.Status.IDError):
                            pixels[i] = [255*brightness,0,255*brightness]

        for i in range(len(slots)):
            if i not in slots_updated:
                for x in slots[i]:
                    pixels[x] = [0,0,0]
            
        if(lightStatus == LightStatus.Loading):
            for slot in slots:
                for i in slot:
                    pixels[i] = [0,0,255*brightness*mod_brightness]
        if(lightStatus == LightStatus.JSONError):
                    pixels[1] = [255*brightness*mod_brightness,0,0]
        if(lightStatus == LightStatus.Loading):
            for slot in slots:
                for i in slot:
                    pixels[i] = [255*brightness*mod_brightness,0,255*brightness*mod_brightness]
        time.sleep(.01);
        
x = threading.Thread(target=lightThread)

slots = getConfigSlots()

x.start()



intents = intents = discord.Intents.all()
client = discord.Client(intents=intents)
        
lightStatus = LightStatus.Loaded

def updateUsernames():
    for friend in friends:
        if(friend.member!=None):
            if(friend.member.name != friend.getName()):
                friend.setName(friend.member.name)

def updateFriendStatus():
    for friend in friends:
        if(friend.member != None):
            if((friend.member.is_on_mobile()) and (friend.mobileStatus == False)):
                continue
            if(friend.member.status==discord.Status.online):
                friend.status = friend.Status.Online
            if(friend.member.status==discord.Status.idle):
                friend.status = friend.Status.Away
            if(friend.member.status==discord.Status.dnd):
                friend.status = friend.Status.Dnd
            if(friend.member.status==discord.Status.dnd):
                friend.status = friend.Status.Dnd
            if(friend.member.status==discord.Status.offline):
                friend.status = friend.Status.Offline
            if friend.member.activity !=None:
                if friend.member.activity.type == discord.ActivityType.playing:
                    friend.status = friend.Status.Ingame
                    if(friend.isFavGame(friend.member.activity.name)):
                        friend.status = friend.Status.Favgame
        else:
            friend.status = friend.Status.IDError


def loadConfig():
    friends.clear();
    for i in range(0, len(config["Users"])):
        friend = Friend(getConfigUserName(i), getConfigUserID(i), getConfigUserSlot(i), getConfigUserMobileStatus(i), getConfigUserFavoriteGames(i), None,i)
        friends.append(friend)
    for friend in friends:
        if((int(friend.getID())==-1) or(int(friend.getID())==0)):
            name = friend.getName()
            print (name)
            member = None
            for mem in getGuildMembers():
                if(mem.name == name):
                    if(member!=None):
                        logging.error('Found multiple players with that name: {0}'.format(name)) ##Add light error code
                        continue
                    member = mem
            if(member==None):
                logging.error ("Could not find player with name: {0}".format(name)) ##Add light error code
                continue
            friend.setID(int(member.id))
    
    for mem in getGuildMembers():
        for friend in friends:
                if(friend.getID() == int(mem.id)):
                    friend.member = mem

def loop():
    updateFriendStatus()

@client.event
async def on_ready():
    logging.info('We have logged in as {0.user}'.format(client))
    logging.info('Connected to server {0} aka {1}'.format(getConfigGuildID(), getGuild().name))
    loadConfig()
    updateUsernames()
    updateFriendStatus()


    schedule.every(60).seconds.do(loop)
    schedule.every(20).minutes.do(updateUsernames)

    while True:
        schedule.run_pending()
        await asyncio.sleep(1)

@client.event
async def on_member_update(before, after):
    updateFriendStatus()

def checkInternetUrllib(url='http://google.com', timeout=3):
    try:
        urllib.request.urlopen(url, timeout=timeout)
        return True
    except Exception as e:
        return False

while(checkInternetUrllib()==False):
    time.sleep(1)
    lightStatus = LightStatus.WIFIError

lastBotToken = getConfigBotToken()
client.run(getConfigBotToken())


