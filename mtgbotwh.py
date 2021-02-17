#!/usr/bin/env python

import telepot
import pymysql.cursors
import logging
import sys
import http.server
import socketserver
import json
import hashlib
import datetime
import threading

from queue import Queue
from threading import Thread 

from telepot.loop import MessageLoop
from time import sleep,time
from configobj import ConfigObj

from lib.dbcheck import db_need_update
from lib.logfile import log

pvp = 0

def install_thread_excepthook():
	run_old = threading.Thread.run
	def run(*args, **kwargs):
		try:
			run_old(*args, **kwargs)
		except (KeyboardInterrupt, SystemExit):
			raise
		except:
			sys.excepthook(*sys.exc_info())
	threading.Thread.run = run

# Webhook Handler
#
class WebhookHandler(http.server.BaseHTTPRequestHandler):

	def do_POST(self):
		content_len = int(self.headers.get('content-length', 0))
		self.wfile.write("HTTP/1.1 200 OK".encode("utf-8"))

		# Json formatting
		#
		jsonlist = self.rfile.read(content_len)
		messages = json.loads(jsonlist)

		# Loop over all messages
		#
		for message in messages:
			msgtype=(message['type'])

			if msgtype == "pokemon":

				message=message['message']

				# check duplicate message
				jdump=json.dumps(message, sort_keys = True).encode("utf-8")
				md5=hashlib.md5(jdump).hexdigest()
				despawn=message['disappear_time']

				if md5 not in duplicatemsg:
					pkmn_queue.put(message)
					duplicatemsg[md5]=despawn

# Bot was blocked
#
def bot_was_blocked(botid,chat_id):
	log("Bot was blocked. Stopping ChatId {}".format(chat_id),"webhook")
	cursor.execute("delete from user where botid = '%s' and chatid = '%s'" % (botid,chat_id))
	cursor.execute("select count(*) from user where chatid = '%s'" % (chat_id))
	result = cursor.fetchone()
	if result[0] == 0:
		cursor.execute("insert ignore into userstop values ('%s', CURRENT_TIMESTAMP)" % (chat_id))

# convert Message
#
def textsub(text,message):
	text = text.replace("\\n","\n")
	text = text.replace("<pkmn>",str(message['name']))
	text = text.replace("<pkmnid>",str(message['pokemon_id']))
	text = text.replace("<despawn>",str(message['despawn']))
	text = text.replace("<iv>",str(message['iv']))
	text = text.replace("<cp>",str(message['cp']))
	text = text.replace("<atk>",str(message['individual_attack']))
	text = text.replace("<def>",str(message['individual_defense']))
	text = text.replace("<sta>",str(message['individual_stamina']))
	text = text.replace("<lvl>",str(message['pokemon_level']))
	return(str(text))

# Reorg duplicate messages
def reorg_duplicate():

	while True:
		deleted=0
		reorgtime=int(time())
		for n in list(duplicatemsg):
			if duplicatemsg[n] < reorgtime:
				duplicatemsg.pop(n)
				deleted += 1
		log("Reorg duplicate Messages. Deleting {}/{}".format(deleted,len(list(duplicatemsg.keys()))),"webhook")
		sleep(10)

# send monster to user
#
def sendmonster(pkmn_queue,pkmn_loc):

	while True:
		message = pkmn_queue.get()

		pkmn_id=(message['pokemon_id'])

		# set monster info
		#
		pkmn_name = pkmn_loc[str(pkmn_id)]["name"]
		pkmn_despawn = datetime.datetime.fromtimestamp( int(message['disappear_time'])).strftime('%H:%M:%S')

		log("{}({}) until {} @ {},{}".format(pkmn_name,pkmn_id,pkmn_despawn,message['latitude'],message['longitude']),"webhook")

		# calculate IV if encounting
		#
		try:
			pkmn_iv = round(((message['individual_attack'] + message['individual_defense'] + message['individual_stamina']) * 100 / 45))
			log("IV:{:.2f} CP:{:4d} ATT:{:2d} DEF:{:2d} STA:{:2d}".format(pkmn_iv,message['cp'],message['individual_attack'],message['individual_defense'],message['individual_stamina']),"webhook")
		except:
			pkmn_iv = "None"
			message['individual_attack'] = "??"
			message['individual_defense'] = "??"
			message['individual_stamina'] = "??"
			message['cp'] = "??"
			message['pokemon_level'] = "??"

		# add missing data to message
		message['iv'] = pkmn_iv
		message['name'] = pkmn_name
		message['despawn'] = pkmn_despawn

		connection.ping(reconnect=True)
		cursor.execute("select userassign.chatid,iv,u.pvponly from userassign join user as u on userassign.chatid = u.chatid where pkmnid = '%s' and \
				userassign.chatid not in (select chatid from userblock) and \
				userassign.chatid in (select chatid from user where botid = '%s') and \
				userassign.chatid in (SELECT chatid FROM user WHERE '%s' BETWEEN IfNull(latitude,-90)-IfNull(distance,0)/100 AND IfNull(latitude,90)+IfNull(distance,0)/100 AND '%s' BETWEEN IfNull(longitude,-180)-IfNull(distance,0)/100 AND IfNull(longitude,180)+IfNull(distance,0)/100)" % (pkmn_id,botid,message['latitude'],message['longitude']))
# IF(is_shiny, worker, 'x96mini0') AS worker, IfNull(t.is_shiny, 0) AS is_shiny,
		result_pkmn = cursor.fetchall()
		print(result_pkmn)
#		print(message['latitude'],message['longitude'])

		if len(result_pkmn) > 0:
			#send monster message to all
			#
			for chat_id,iv,pvponly in result_pkmn:
				if message['iv'] == "None":
					if iv == -1:
						venuetitle1 = textsub(venuetitle,message)
						venuemsg1 = textsub(venuemsg,message)
						try:
							bot.sendVenue(chat_id,message['latitude'],message['longitude'],venuetitle1,venuemsg1)
							log("Send Telegram Message to {} Monster {}({})".format(chat_id,pkmn_name,pkmn_id),"webhook")
						except telepot.exception.BotWasBlockedError:
							bot_was_blocked(botid,chat_id)
						except telepot.exception.TooManyRequestsError:
							pkmn_queue.put(message)
							log("To many Requests. Sleep 1 sec.","webhook")
							sleep(1)
						except:
							log("ERROR IN SENDING TELEGRAM MESSAGE TO {}".format(chat_id),"webhook")
							log("Error: {}".format(sys.exc_info()[0]),"webhook")
					else:
						log("No message send to {}. SearchIV set but Monster {}({}) not encountered".format(chat_id,pkmn_name,pkmn_id),"webhook")
				else:

					if pvponly == 1:
						iv = 0
					if message['iv'] >= iv:
						ivmsg1 = textsub(ivmsg,message)
						try:
							for great in message['pvp_rankings_great_league']:
								if great['cp'] >= 1300:
									pkmn_nameGL = pkmn_loc[str(great['pokemon'])]["name"]
									print("GL R:" + str(great['rank']) + " L:" + str(great['level']) + " CP:" + str(great['cp'])+ " " + str(great['percentage']) + "% Dex:" + str(great['pokemon']) + " Form:" + str(great['form'])+"\n")
									greatmsg = "🅿️R:" + str(great['rank']) + " L:" + str(great['level']) + " CP:" + str(great['cp'])+ " " + str(great['percentage']) + "% " + str(pkmn_nameGL) + "\n"
#									greatmsg = "🅿️R:" + str(great['rank']) + " L:" + str(great['level']) + " CP:" + str(great['cp'])+ " " + str(great['percentage']) + "% Dex:" + str(great['pokemon']) + " Form:" + str(great['form'])+"\n"
									ivmsg1 += greatmsg
									pvp = 1
								else:
									pvp = 0
						except:
							pvp = 0
						try:
							for ultra in message['pvp_rankings_ultra_league']:
								if ultra['cp'] >= 2300:
									pkmn_nameUL = pkmn_loc[str(ultra['pokemon'])]["name"]
									print("UL R:" + str(ultra['rank']) + " L:" + str(ultra['level']) + " CP:" + str(ultra['cp'])+ " " + str(ultra['percentage']) + "% Dex:" + str(ultra['pokemon']) + " Form:" + str(ultra['form'])+"\n")
									ultramsg = "🆚R:" + str(ultra['rank']) + " L:" + str(ultra['level']) + " CP:" + str(ultra['cp'])+ " " + str(ultra['percentage']) + "% " + str(pkmn_nameUL) +"\n"
#									ultramsg = "🆚R:" + str(ultra['rank']) + " L:" + str(ultra['level']) + " CP:" + str(ultra['cp'])+ " " + str(ultra['percentage']) + "% Dex:" + str(ultra['pokemon']) + " Form:" + str(ultra['form'])+"\n"
									ivmsg1 += ultramsg
									pvp = 1
								else:
									pvp = 0
						except:
							pvp = 0

						if (pvponly == 1 and pvp == 1) or pvponly == 0:
							try:
								bot.sendMessage(chat_id,ivmsg1)
								bot.sendLocation(chat_id,message['latitude'],message['longitude'])
								log("Send Telegram IV Message to {} Monster {}({})".format(chat_id,pkmn_name,pkmn_id),"webhook")
							except telepot.exception.BotWasBlockedError:
								bot_was_blocked(botid,chat_id)
							except telepot.exception.TooManyRequestsError:
								pkmn_queue.put(message)
								log("To many Requests. Sleep 1 sec.","webhook")
								sleep(1)
							except:
								log("ERROR IN SENDING TELEGRAM MESSAGE TO {}".format(chat_id),"webhook")
								log("Error: {}".format(sys.exc_info()[0]),"webhook")
						else:
							log("No message send to {}. PvP Only Mode for Monster {}({})".format(chat_id,pkmn_name,pkmn_id),"webhook")
					else:
						log("No message send to {}. SearchIV to low for Monster {}({})".format(chat_id,pkmn_name,pkmn_id),"webhook")

##### MAIN #####

def my_excepthook(excType, excValue, traceback, logger=logging):
	logging.error("Logging an uncaught exception",
		exc_info=(excType, excValue, traceback))

sys.excepthook = my_excepthook

install_thread_excepthook()

# read inifile
#
try:
	config = ConfigObj("config.ini")

	token=config['token']
	db = config['dbname']
	dbhost = config['dbhost']
	dbport = config.get('dbport', '3306')
	dbuser = config['dbuser']
	dbpassword = config['dbpassword']
	whport = int(config.get('port', '6000'))
	venuetitle = config['venuetitle']
	venuemsg = str(config['venuemsg'])
	ivmsg = str(config['ivmsg'])
	locale = str(config.get('locales','de'))
###	pvponly = int(config['pvponly'])
except:
	botname = "None"
	log("Error in config.ini","webhook")
	quit()

# connect to database
#
try:
	connection = pymysql.connect(host=dbhost,
		user=dbuser,
		password=dbpassword,
		db=db,
		port=int(dbport),
		charset='utf8mb4',
		autocommit='True')
	cursor = connection.cursor()
except:
	log("can not connect to database","webhook")
	quit()

if db_need_update(cursor):
	log("Your DB-Version is to low. Please start dbupdate.py first","webhook")
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
	log("Error in Telegram. Can not find Botname and ID","webhook")
	quit()

# queue for pkmninfo
#
pkmn_queue = Queue()
duplicatemsg={}

# Thread to process pokemon
pkmn_loc = json.load(open("locales/monster_" + locale + ".json"))
worker = Thread(target=sendmonster, args=(pkmn_queue,pkmn_loc))
worker.setDaemon(True)
worker.start()

reorg = Thread(target=reorg_duplicate)
reorg.setDaemon(True)
reorg.start()

# create Server
#
try:
	httpd = socketserver.TCPServer(("", whport), WebhookHandler )
	httpd.allow_reuse_address = True
	log("MonsterGBot {} serving at port {}".format(botname,whport),"webhook")
except:
	print ("Port still open, wait a minute before restart")

try:
	httpd.serve_forever()
finally:
	print ("Server closed")
	httpd.shutdown()
	httpd.server_close()

