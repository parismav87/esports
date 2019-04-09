# -*- coding: utf-8 -*-
import sys
import os
import xlrd
import math
import datetime
import csv
import calendar
import matplotlib.pyplot as plt
import json
import numpy as np
from biosppy.signals import bvp
from biosppy.signals import eda

sessionArray = {}
participantArray = {}
gameArray = {}
apmInterval = 1000 #interval to calculate APM in millis
hrInterval = 20 #interval to calculate HR in seconds
samplingRate = 20 #Hz

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
		self.rawHeartrates = {}
		self.rawSkinconductances = {}
		self.heartrates = {}
		self.skinconductances = {}
		self.readBasicData()
		self.timestamps = []

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
				d = str(date[2])
				m = str(date[1])
				y = str(date[0])
				self.dateString = ("0"+d)[-2:] + "-" + ("0"+m)[-2:] + "-" + y  # d-m-y
				# print self.dateString
			else: # game id 
				# self.games = d.split(",")
				pass
		# print self.participants[0]


	def generateTimestamps(self):
		minStart = 99999999999999999999
		maxEnd = 0
		for g in self.games:
			if g.start < minStart:
				minStart = g.start
			if g.end > maxEnd:
				maxEnd = g.end
		minStart = getSessionStart(minStart)
		maxEnd = getSessionEnd(maxEnd)
		# print minStart,"-",maxEnd
		temp = minStart
		while temp<=maxEnd:
			self.timestamps.append(temp)
			temp += 500
		# print self.timestamps

	def readPhysiological(self, path, folder):
		for f in folder:
			if "sensor" in f:
				participantid = f.split("-")[0] + "-" + f.split("-")[1] # lol-X
				with open(path+"/"+f) as log:
					fullLog = csv.reader(log, delimiter='\t')
					self.parsePhysiological(fullLog, participantid)

		# for s in self.skinconductances:
		# 	plt.plot(self.skinconductances[s])
		# for h in self.heartrates:
		# 	plt.plot(self.heartrates[h])
		# plt.show()

	def parsePhysiological(self, log, participantid):
		print "Participant: ", participantid
		rawSCArr = []
		rawHRArr = []
		hrUnfiltered = []
		scUnfiltered = []
		scFiltered = []
		hrFiltered = []
		timestamps = []
		heartrates = {}
		skinconductances = {}

		for ts in self.timestamps:
			heartrates[ts] = {
				'measurements': [],
				'value': 0
			}
			skinconductances[ts] = {
				'measurements': [],
				'value': 0
			}

		hrRange = (1000/samplingRate)*hrInterval #range for BPM calculation in Number of measurements (array positions)
		for k,v in enumerate(log):
			if k>2:
				ts = int(float(v[0]))
				timestamps.append(ts)
				hrUnfiltered.append(float(v[13]))
				scUnfiltered.append(float(v[8]))

		numberOfMeasurements = len(hrUnfiltered)
		# print numberOfMeasurements, "--", participantid

		scFiltered = scUnfiltered

		for k,v in enumerate(hrUnfiltered):
			# print k , " - ", numberOfMeasurements, " - ", participantid
			measurement = None
			sample = []
			if k>hrRange/2 and k<numberOfMeasurements-hrRange/2:
				sample = hrUnfiltered[k-hrRange/2:k+hrRange/2]
			elif k<hrRange/2:
				sample = hrUnfiltered[0:hrRange]
			else:
				sample = hrUnfiltered[numberOfMeasurements-hrRange:numberOfMeasurements-1]


			try:
				bvpArr = bvp.bvp(sample,20,show=False)
				measurement = np.nanmean(bvpArr["heart_rate"])
				hrFiltered.append(measurement)
			except: 
				# print("could not compute bpm")
				measurement = hrFiltered[k-1]
				hrFiltered.append(measurement)
			# print measurement

		for k,v in enumerate(hrFiltered):
			modulo = timestamps[k]%500
			tsRounded = timestamps[k]-modulo
			if tsRounded in self.timestamps:
				heartrates[tsRounded]['measurements'].append(v)
				skinconductances[tsRounded]['measurements'].append(scFiltered[k])
		for m in heartrates:
			heartrates[m]['value'] = np.nanmean(heartrates[m]['measurements'])
			skinconductances[m]['value'] = np.nanmean(skinconductances[m]['measurements'])

		# print heartrates

		
		# self.rawSkinconductances[participantid] = rawSCArr
		# self.rawHeartrates[participantid] = rawHRArr

		self.heartrates[participantid] = heartrates
		self.skinconductances[participantid] = skinconductances

		print "YOLO"
		print len(self.heartrates[participantid])
		print len(self.timestamps)

		# print len(timestamps), "-----", len(hrFiltered)

	def readApm(self, path, folder):
		for f in folder:
			if "keylogger" in f:
				participantid = f.split("-")[0] + "-" + f.split("-")[1] # lol-X
				print participantid
				with open(path+"/"+f) as log:
					fullLog = csv.reader(log, delimiter='\t')
					parsedLogs = self.parseApm(fullLog)
					self.logs[participantid] = parsedLogs
					self.calculateApm(participantid)


	def parseApm(self, log):
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

	def calculateApm(self, participantid):
		epoch = datetime.datetime.utcfromtimestamp(0)
		# print self.logs
		apmClick = {}
		apmKeyboard = {}
		# toplot = []
	
		for ts in self.timestamps:
			apmClick[ts] = {
				'value': 0
			}
			apmKeyboard[ts] = {
				'value': 0
			}
		# print apmClick
		for k,log in enumerate(self.logs[participantid]):	
			# print ts
			timestamp = log['timestamp']
			dt = datetime.datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%f")
			unixTimestamp = int((dt-epoch).total_seconds()*1000.0)
			modulo = unixTimestamp%500
			tsRounded = unixTimestamp - modulo
			if "Key" in log['action']: #keyboard
				if tsRounded in apmKeyboard:
					apmKeyboard[tsRounded]['value'] +=1
			elif "Pressed" in log['action']: #mouse click
				if tsRounded in apmClick:
					apmClick[tsRounded]['value'] +=1
		for v in apmClick:
			apmClick[v]['value'] *=120 
			apmKeyboard[v]['value'] *= 120

		self.apms[participantid] = {
			'mouse': apmClick,
			'keyboard': apmKeyboard
		}

	def readGameData(self, path, folder):
		for f in folder: 
			if "matchid" in f:
				gameid = f.split("-")[1].split(".")[0].strip()
				print "gameid: ",gameid
				g = Game(gameid)
				gameArray[gameid] = g
				self.games.append(g)

				# print self.games

				jsonFile = open(path+"/"+f)
				jsonString = jsonFile.read()
				jsonData = json.loads(jsonString)

				start = jsonData['gameCreation']
				duration = jsonData['gameDuration']
				# print start , " !!!!!!!!!!!"
				# g.start = float(start) / 1000 # millis to seconds
				g.start = int(start)
				# g.start = g.start + 3600000 #correct for timezone difference (sensor data is in local time)
				g.end = g.start + int(duration*1000) #duration is in seconds
				# print str(g.start) + "   " + str(g.end) 
				g.participants = g.getGameParticipants(jsonData)
				g.win = g.getGameWin(jsonData)
				print g.participants
				print "-"
				print g.win


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
		self.win = False
		self.participants = []
		self.stats = []

	def getGameParticipants(self, json):
		arr = []
		for p in participantArray:
			par = participantArray[p]
			for n in par.ingame:
				for participant in json['participantIdentities']:
					if "player" not in participant:
						return ['unknown']
					name=participant['player']['summonerName']
					if name.replace(" ","").lower()==n.replace(" ","").lower():
						arr.append(par.id)
		return arr



	def getGameWin(self, json):
		teamWin = 0
		for t in json["teams"]:
			if t["win"]=="Win":
				teamWin = t["teamId"]
		for p in participantArray:
			par = participantArray[p]
			for n in par.ingame:
				if "player" not in json["participantIdentities"][5]:
					return "UNKNOWN"
				if json["participantIdentities"][5]["player"]["summonerName"].replace(" ","").lower() == n.replace(" ","").lower(): #1st player of red team
					if teamWin==200:
						return True
				elif json["participantIdentities"][0]["player"]["summonerName"].replace(" ","").lower() == n.replace(" ","").lower(): #1st player of blue team
					if teamWin==100:
						return True
		return False

	def participantsString(self):
		string = ""
		for p in self.participants:
			string = string + p + ","
		return string[:-1] # remove last comma

class Keylog(object):
	def __init__(self, participantid, gameid):
		self.participantid = participantid
		self.gameid = gameid
		self.logs = []

def getSessionStart(number):
	# print number
	startNotRounded = number - 600000 # -10 mins
	modulo = startNotRounded%500
	return startNotRounded - modulo

def getSessionEnd(number):
	# print number
	endNotRounded = number + 600000 # +10 mins
	modulo = endNotRounded%500
	return endNotRounded - modulo

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
						ses.generateTimestamps()
						ses.readApm(fullPath, sessionFolder)
						ses.readPhysiological(fullPath, sessionFolder)
						

def createCSV():

	print "creating CSV"
	for s in sessionArray:
		ses = sessionArray[s]
		# print "len timestamps ", len(ses.timestamps)
		if not os.path.exists(ses.dateString):
			os.makedirs(ses.dateString)
		for p in ses.participants:	
			pid = str(p.id)
			filename = ses.dateString+'/'+p.id+".csv"
			with open(filename, 'wb') as csvfile:
				writer = csv.writer(csvfile, delimiter=',')
				writer.writerow(["timestamp", "HR", "SC", "APMMouse", "APMKeyboard"])				
				print pid
				print ses.dateString
				print "------"
				print "len heartrates ", len(ses.heartrates[pid])
    			# print ses.apms
    			# print p.id
    			# print ses.heartrates
				for t in ses.timestamps:
					# print "---------->",t
					arr = []
					HRString = '-'
					SCString = '-'
					APMMouseString = '-'
					APMKeyboardString = '-'
					if t in ses.heartrates[pid]:
						HRString = str(ses.heartrates[pid][t]['value'])
						# if HRString == "nan":
						# 	print ses.heartrates[pid][t]['measurements']
						# 	print ses.heartrates[pid][t]['value']
					if t in ses.skinconductances[pid]:
						SCString = str(ses.skinconductances[pid][t]['value'])
					if t in ses.apms[pid]['mouse']:
						APMMouseString = str(ses.apms[pid]['mouse'][t]['value'])
					if t in ses.apms[pid]['keyboard']:
						APMKeyboardString = str(ses.apms[pid]['keyboard'][t]['value'])
					arr.append(str(t))
					arr.append(HRString)
					arr.append(SCString)
					arr.append(APMMouseString)
					arr.append(APMKeyboardString)
					writer.writerow(arr)
				# print len(arr)
		filename = ses.dateString+'/'"games.csv"
		with open(filename, 'wb') as csvfile:
			writer = csv.writer(csvfile, delimiter=',')
			writer.writerow(["id", "start", "end", "win", "participants"])
			for g in ses.games:
				arr = []
				arr.append(str(g.id))
				arr.append(str(g.start))
				arr.append(str(g.end))
				arr.append(str(g.win))
				arr.append(g.participantsString())
				writer.writerow(arr)


# ------------------------- MAIN ------------------------------#
if len(sys.argv)>1:
	path = sys.argv[1]
	files = os.listdir(path)
	readParticipants(files)
	readSessions(files)
	createCSV()
	# readGames(files)
	