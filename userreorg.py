#! /usr/bin/python

import telepot
import pymysql.cursors
import logging
import sys
import datetime
import time

from configobj import ConfigObj

from lib.dbcheck import db_need_update

# Logging
#
def log(msg):
        print (msg)
        logging.basicConfig(filename="log/userreorg.log", format="%(asctime)s|%(message)s", level=logging.INFO)
        logging.info(msg)

##### MAIN #####

def my_excepthook(excType, excValue, traceback, logger=logging):
    logging.error("Logging an uncaught exception",
                 exc_info=(excType, excValue, traceback))

sys.excepthook = my_excepthook

# read inifile
#
try:
        inifile = sys.argv[1]
        config = ConfigObj(inifile)

        db = config['dbname']
        dbhost = config['dbhost']
        dbport = config.get('dbport', '3306')
        dbuser = config['dbuser']
        dbpassword = config['dbpassword']
	reorgdays = int((config.get('reorgdays', '180')))
except:
        log("Inifile not given or missing parameter")
        quit()

dryrun = 0
try:
	dryrun = sys.argv[2]
	if dryrun == '-n':
		dryrun = 1
		log("Dryrun")
except:
	pass

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
        log("can not connect to database")
        quit()

if db_need_update(cursor):
        log("Your DB-Version is to low. Please start dbupdate.py first")
        quit()

cursor.execute("select chatid from userstop where timestampdiff(DAY,stopdate,CURRENT_TIMESTAMP) > '%s'" % (reorgdays))
result = cursor.fetchall()
for row in result:
	log("Delete Chatid {}".format(row[0]))
	if dryrun == 0:
		try:
			cursor.execute("delete from userassign where chatid = '%s'" % (row[0]))
			cursor.execute("delete from userstop where chatid = '%s'" % (row[0]))
		except:
			log("Error in deleting chatid from userassign")

