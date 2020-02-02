#! /usr/bin/python

import telepot
import pymysql.cursors
import logging
import sys
import json

from telepot.loop import MessageLoop
from time import sleep
from configobj import ConfigObj

from lib.dbcheck import db_need_update
from lib.logfile import log

def sendtelegram(chatid,msg):
	try:
		bot.sendMessage(chatid, msg)
	except:
		log ("ERROR IN SENDING TELEGRAM MESSAGE TO {}".format(chatid),"user")


# Handle for incomming Commands
def handle(msg):
	content_type, chat_type, chat_id = telepot.glance(msg)
	if content_type != 'text':
		return

	fromwho = msg.get('from')
	username = fromwho.get('username', '')
	vname = fromwho.get('first_name', '')
	nname = fromwho.get('last_name', '')

	log("Message from ID: {}:{}:{}".format(str(chat_id),username,msg['text']),"user")

	command = msg['text'].split("@")[0].split(" ")[0]

	try:
		connection.ping(reconnect=True)
		cursor.execute("select count(*) from userblock where chatid = '%s'" % (chat_id))
		result = cursor.fetchone()
		if result[0] == 1:
			sendtelegram(chat_id,msg_loc["19"])
			command=""
	except:
		sendtelegram(chat_id,msg_loc["6"])
		command=""

	if command == "/help":
		msg = ""
		helplist = msg_loc["1"].split("\n")
		for i in helplist:
			msg = msg + "{} :\n{}\n".format(i.split(":")[0].encode("utf-8"),i.split(":")[1].encode("utf-8"))
		bot.sendMessage(chat_id, msg)

	elif command == "/start":
		msg = ""
		startmsg = open(invstartmsg, "r")
		for line in startmsg:
			msg = msg + "{}".format(line)
		sendtelegram(chat_id,msg)
		startmsg.close()
		
		try:			# delete chatid from Stop Table
			cursor.execute("delete from userstop where chatid = '%s'" % (chat_id))
		except:
			pass
		try:			# insert users information and the bot id
			cursor.execute("insert into user values ('%s','%s','%s','%s','%s',current_timestamp)" % (botid,username,vname,nname,chat_id))
		except:
			pass
		sendtelegram(chat_id,msg_loc["2"])

	elif command == "/stop":
		try:			# delete user data
			cursor.execute("delete from user where botid = '%s' and chatid = '%s'" % (botid,chat_id))
		except:
			pass
		try:			# and if no bot left insert chatid in stop table for reorg
			cursor.execute("select count(*) from user where chatid = '%s'" % (chat_id))
			result = cursor.fetchone()
			if result[0] == 0:
				cursor.execute("insert ignore into userstop values ('%s', CURRENT_TIMESTAMP)" % (chat_id))
		except:
			pass
		sendtelegram(chat_id,msg_loc["3"])

	elif command == "/status":	# send user staus of his bot
		cursor.execute("select count(*) from user where botid = '%s' and chatid = '%s'" % (botid,chat_id))
		result = cursor.fetchone()
		if result[0] > 0:
			sendtelegram(chat_id,msg_loc["4"])
		else:
			sendtelegram(chat_id,msg_loc["5"])

	elif command == "/mydata":	# send users stored information
		cursor.execute("select botid,username,vorname,nachname,chatid from user where chatid = '%s'" % (chat_id))
		result = cursor.fetchall()
		if result:
			for row in result:
				cursor.execute("select botname from bot where botid = '%s'" % (row[0]))
				botname = cursor.fetchone()
				msg = str(msg_loc["21"].format(row[1],row[2],row[3],row[4]).encode("ascii", errors='ignore'))
				sendtelegram(chat_id,msg)
		else:
			sendtelegram(chat_id,msg_loc["22"])

	elif command == "/deleteall":	# delete user completely
		cursor.execute("delete from userassign where chatid = '%s'" % (chat_id))
		cursor.execute("delete from user where chatid = '%s'" % (chat_id))
		cursor.execute("delete from userstop where chatid = '%s'" % (chat_id))
		sendtelegram(chat_id,msg_loc["20"])

	elif command == "/list":	# list monsterlist to user
                cursor.execute("select pkmnid,iv from userassign where chatid = '%s'" % (chat_id))
		result_p = cursor.fetchall()

		msg = str(msg_loc["16"]) + "\n"
		for row in result_p:
			msg = msg + "{} : {} : {}\n".format(row[0],pkmn_loc[str(row[0])]["name"].encode("utf-8"),row[1])
		while len(msg) > 0:	# cut message to telegram max messagesize
			msgcut = msg[:4096].rsplit("\n",1)[0]
			sendtelegram(chat_id, msgcut)
			msg = msg[len(msgcut)+1:]

	elif command == "/add":		# add Pokemon to list
		pkmniv = 0

		try:
			pkmnid = msg['text'].split(" ")[1]
		except:
			sendtelegram(chat_id,msg_loc["7"] + "/add")
			return

		try:
			pkmniv = int(msg['text'].split(" ")[2])
		except:
			pass

		if pkmniv > 100:
			pkmniv = 100
		
		try:
			pkname = pkmn_loc[str(pkmnid)]["name"]
			try:
				cursor.execute("insert into userassign values ('%s','%s','%s')" % (pkmnid,chat_id,pkmniv))
				sendtelegram(chat_id, pkname + msg_loc["8"])
			except:
				sendtelegram(chat_id, pkname + msg_loc["9"])
		except:
			sendtelegram(chat_id, str(pkmnid) + msg_loc["10"])

	elif command == "/del":		# delete Pokemon from list
		try:
			pkmnid = msg['text'].split(" ")[1]
		except:
			sendtelegram(chat_id,msg_loc["7"] + "/del")
			return

		try:
			pkname = pkmn_loc[str(pkmnid)]["name"]
			if cursor.execute("delete from userassign where chatid = '%s' and pkmnid = '%s'" % (chat_id,pkmnid)):
				sendtelegram(chat_id, pkname + msg_loc["12"])
			else:
				sendtelegram(chat_id, pkname + msg_loc["13"])
		except:
			sendtelegram(chat_id, str(pkmnid) + msg_loc["10"])

	elif command == "/setiv":	# set IV to Pokemon
		try:
			pkmnid = int(msg['text'].split(" ")[1])
			pkmniv = int(msg['text'].split(" ")[2])
		except:
			sendtelegram(chat_id, msg_loc["14"])
			return

		if pkmniv > 100:
			pkmniv = 100

		try:
			pkname = pkmn_loc[str(pkmnid)]["name"]
			if cursor.execute("update userassign set iv = '%s' where chatid = '%s' and pkmnid = '%s'" % (pkmniv,chat_id,pkmnid)):
				sendtelegram(chat_id, msg_loc["15"].format(str(pkmniv),pkname))
			else:
				sendtelegram(chat_id, pkname + msg_loc["13"])
		except:
			sendtelegram(chat_id, str(pkmnid) + msg_loc["10"])

	else:
		if command[:1] == '/':
			sendtelegram(chat_id, command + msg_loc["17"])

### _MAIN_ ###

def my_excepthook(excType, excValue, traceback, logger=logging):
	logging.error("Logging an uncaught exception",
		exc_info=(excType, excValue, traceback))

sys.excepthook = my_excepthook
logname="user"

# read inifile
try:
	config = ConfigObj("config.ini")
	token=config.get('token')
	db = config['dbname']
	dbhost = config['dbhost']
	dbport = config.get('dbport', '3306')
	dbuser = config['dbuser']
	dbpassword = config['dbpassword']
	locale = config.get('locale', 'de')
	invstartmsg = config.get('startmsg', "locales/startmsg_" + locale + ".txt")
except:
	log("Error in config.ini",logname)
	quit()

# connect to database
#
try:
	connection = pymysql.connect(
		host=dbhost,
		user=dbuser,
		password=dbpassword,
		db=db,
		port=int(dbport),
		charset='utf8mb4',
		autocommit='True')
	cursor = connection.cursor()
except:
	log("can not connect to database","user")
	quit()

if db_need_update(cursor):
	log("Your DB-Version is to low. Please start dbupdate.py first","user")
	quit()

# get bot information
#
bot = telepot.Bot(token)
try:
	botident = bot.getMe()
	botname = botident['username']
	botcallname = botident['first_name']
	botid = botident['id']
	try:
		cursor.execute("insert into bot values ('%s','%s')" % (botid,botname))
	except:
		pass
except:
	log("Error in Telegram. Can not find Botname and ID","user")
	quit()

pkmn_loc = json.load(open("locales/monster_" + locale + ".json"))
msg_loc = json.load(open("locales/msg_" + locale + ".json"))

# Main Loop
try:

	MessageLoop(bot, handle).run_as_thread()

	log("Bot {} started".format(botname),"user")

	while True:
		sleep(60)

except KeyboardInterrupt:
	pass
