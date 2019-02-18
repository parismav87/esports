# -*- coding: utf-8 -*-
import sys
import os
import xlrd
import datetime
import csv
import calendar
import matplotlib.pyplot as plt
import json

sessionArray = {}
participantArray = {}
gameArray = {}
apmInterval = 60 #interval to calculate APM in seconds

class Session(object):
	def __init__(self, data, book):
		self.data = data
		self.book = book
		self.path = path
		self.date = ""
		self.dateString = ""
		self.participants = []
		self.games = []
		self.logs = {}
		self.apms = {}
		self.readBasicData()

	def readBasicData(self):
		# print self.data
		for d in self.data:
			# print d
			if isinstance(d, basestring) and "lol" in d: #participant id
				participants = d.split(",")
				for p in participants:
					for k, pa in participantArray.items():
						if p.strip() == pa.id:
							self.participants.append(pa)
				# print self.participants
			elif isinstance(d, float): #date
				date = xlrd.xldate_as_tuple(d, self.book.datemode)
				self.date = date
				self.dateString = str(date[2]) + "-" + str(date[1]) + "-" + str(date[0])  # d-m-y
				# print self.dateString
			else: # game id
				# self.games = d.split(",")
				pass
		# print self.participants[0]

	def readLogs(self, path, folder):
		for f in folder:
			if "keylogger" in f:
				participantid = f.split("-")[0] + "-" + f.split("-")[1] # lol-X
				print participantid
				with open(path+"/"+f) as log:
					fullLog = csv.reader(log, delimiter='\t')
					parsedLogs = self.parseLogs(fullLog)
					self.logs[participantid] = parsedLogs
					self.calculateApm()


	def parseLogs(self, log):
		playerLog = []
		for k,v in enumerate(log):
			if k>5: #first 5 lines arent logs
				# print v
				obj = {}
				timestamp = v[0]
				obj['timestamp'] = timestamp
				action = v[1]
				obj['action'] = action
				if len(v)>3:
					coords = {
						'x': v[2],
						'y': v[3]
					}
					obj['coords'] = coords
				else: 
					key = v[2]
					obj['key'] = key
				playerLog.append(obj)
		return playerLog

	def calculateApm(self):
		epoch = datetime.datetime.utcfromtimestamp(0)
		# print self.logs
		for playerid in self.logs:
			countAll = 0
			previousAll = 0
			countClick = 0
			previousClick = 0
			countKeyboard = 0
			previousKeyboard = 0
			apmAll = []
			apmClick = []
			apmKeyboard = []
			mouseMove = []
			# print playerid
			
			
			for k,log in enumerate(self.logs[playerid]):	
				timestamp = log['timestamp']
				dt = datetime.datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%f")
				unixTimestamp = (dt-epoch).total_seconds()
				# print "--- "  + str(unixTimestamp)
				if unixTimestamp>=gameArray[self.games[0]].start and unixTimestamp<=gameArray[self.games[0]].end:
					if "Key" in log['action']: #keyboard
						if unixTimestamp - previousKeyboard <= apmInterval:  #read for apm every X seconds
							countKeyboard +=1
						else:
							if countKeyboard>0:
								apmKeyboard.append(countKeyboard*(60/apmInterval))
							countKeyboard = 0
							previousKeyboard = unixTimestamp
					elif "Pressed" in log['action']: #mouse click
						if unixTimestamp - previousClick <= apmInterval:  #read for apm every X seconds
							countClick +=1
						else:
							if countClick>0:
								apmClick.append(countClick*(60/apmInterval))
							countClick = 0
							previousClick = unixTimestamp
					else: # mouse move
						pass

			# plt.plot(apm)
			# plt.show()
			self.apms[playerid] = apmClick
		for k,v in self.apms.items():
			plt.plot(v, label=participantArray[k].name)
		# for g in self.games:
		# 	plt.axvline(x=gameArray[g].start, color="g",  linestyle='--')
		# 	# plt.axvline(x=d.endIndex, color="c", linestyle='--')
		# 	plt.text(gameArray[g].start + 5, 10, "game start", rotation=90, verticalalignment='center')
		# 	# plt.text(d.endIndex + 5, 1, d.dilemmaId, rotation=90, verticalalignment='center')
		plt.legend()
		plt.show()
			

	def readGameData(self, path, folder):
		for f in folder: 
			if "matchid" in f:
				gameid = f.split("-")[1].split(".")[0].strip()
				print gameid
				g = Game(gameid)
				gameArray[gameid] = g
				self.games.append(gameid)

				# print self.games

				jsonFile = open(path+"/"+f)
				jsonString = jsonFile.read()
				jsonData = json.loads(jsonString)

				start = jsonData['gameCreation']
				duration = jsonData['gameDuration']
				g.start = float(start) / 1000 # millis to seconds
				g.start = g.start + 3600 #correct for timezone difference (sensor data is in local time)
				g.end = g.start + float(duration) 
				# print str(g.start) + "   " + str(g.end) 


class Participant(object):
	def __init__(self, id):
		self.id = id
		self.ingame = []
		self.name = ""
		self.games = []

class Game(object):
	def __init__(self, id):
		self.id = id
		self.start = 0
		self.end = 0
		self.participants = []
		self.stats = []

class Keylog(object):
	def __init__(self, participantid, gameid):
		self.participantid = participantid
		self.gameid = gameid
		self.logs = []

def readParticipants(files):
	for name in files:
		if "PARTICIPANTS.xlsx" in name:
			workbook = xlrd.open_workbook(path+"/"+name)
			sheet = workbook.sheet_by_index(0)
			for row in range(sheet.nrows):
				cols = sheet.row_values(row)
				if row!=0:
					p = Participant(cols[1])
					p.ingame = cols[2].split(",")
					p.name = cols[0]
					participantArray[p.id] = p


def readSessions(files):
	for name in files:
		if "SESSIONS.xlsx" in name:
			workbook = xlrd.open_workbook(path+"/"+name)
			sheet = workbook.sheet_by_index(0)
			for row in range(sheet.nrows):
				cols = sheet.row_values(row)
				if row!=0:
					s = Session(cols, workbook)
					sessionArray[s.dateString] = s
		elif name == "sessions": # read each session's user data
			sessions = os.listdir(path + "/" + name)
			for se in sessions:
				fullPath = path + "/" + name + "/" + se
				sessionFolder = os.listdir(fullPath)
				for k, ses in sessionArray.items():
					if se == ses.dateString:
						print "session: " + se
						ses.readGameData(fullPath, sessionFolder)
						ses.readLogs(fullPath, sessionFolder)
						



# ------------------------- MAIN ------------------------------#
if len(sys.argv)>1:
	path = sys.argv[1]
	files = os.listdir(path)
	readParticipants(files)
	readSessions(files)
	readGames(files)
	