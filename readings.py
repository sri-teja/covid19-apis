from libraries import *
from flask import Blueprint


app = Flask(__name__)
CORS(app)

## for logs
# gunicorn_logger = logging.getLogger('gunicorn.error')
# app.logger.handlers = gunicorn_logger.handlers
# app.logger.setLevel(gunicorn_logger.level)

readings = Blueprint('readings', __name__, url_prefix="/readings")

from db_connection import exdb

def new_daily_periodic():
	r = requests.get(url=NEW_SUMMARY_URL) # SUMMARY_URL defined in libraries.py
	data = r.json()
	app.logger.info("calling new daily")
	daily_data = data["cases_time_series"]
	each_country = "India"
	for each in daily_data:
		total = int(each["totalconfirmed"])
		recovered = int(each["totalrecovered"])
		deaths = int(each["totaldeceased"])
		active = total - deaths - recovered

		daily_total = int(each["dailyconfirmed"])
		daily_recovered = int(each["dailyrecovered"])
		daily_deaths = int(each["dailydeceased"])
		daily_active = daily_total - daily_deaths - daily_recovered

		date = each["date"] + "2020"

		ts = str(int((datetime.strptime(date, "%d %B %Y") - datetime(1970, 1, 1)).total_seconds()))

		check = exdb.getData("select * from third_daily where day=\"%s\"" %(date))
		if len(check):
			exdb.editData("update third_daily set total=%d, deaths=%d, recovered=%d, active=%d, daily_total=%d, daily_deaths=%d,\
			 daily_recovered=%d, daily_active=%d, timestamp=\"%s\" where day=\"%s\"" %(total, deaths, recovered, active, daily_total, daily_deaths,\
			  daily_recovered, daily_active, ts, date))
		else:
			exdb.editData("insert into third_daily (total, deaths, recovered, active, daily_total, daily_deaths, daily_recovered,\
			 daily_active, timestamp, day) values (%d, %d, %d, %d, %d, %d, %d, %d, \"%s\", \"%s\")" %(total, deaths, recovered, active, daily_total,\
			  daily_deaths, daily_recovered, daily_active, ts, date))

		## updating india data with covid19india data (this replaces JHU data for India)
		date_data = each["date"] + "2020"
		check = exdb.getData("select * from countrywise where country='India' and day=\"%s\"" %(date_data))
		if len(check):
			fatality_rate = (deaths*1.0/total)*100
			exdb.editData("update countrywise set count=%d, deaths=%d, fatality_rate=%f where country='India' and day=\"%s\"" %(total, deaths, fatality_rate, date_data))

			exdb.editData("update countrywise set mortality_rate=(deaths*1.0/%d) where country='India' and day=\"%s\"" %(POPULATION[each_country]/1000000, date_data))
	
	check = exdb.getData("select count, country, deaths, day from countrywise where country=\"%s\" order by timestamp asc" %(each_country))
	for index, i in enumerate(check):
		if index < (len(check)-1):
			if not index:
				exdb.editData("update countrywise set infection_rate=%f where country=\"%s\" and day=\"%s\"" \
					%(0.0, each_country, check[index]["day"]))
			if check[index]["count"]:
				inf = round(float(check[index+1]["count"])/float(check[index]["count"]), 2)					
				exdb.editData("update countrywise set infection_rate=%f where country=\"%s\" and day=\"%s\"" \
					%(inf, each_country, check[index+1]["day"]))
			else:
				inf = round(float(check[index+1]["count"]), 2)
				exdb.editData("update countrywise set infection_rate=%f where country=\"%s\" and day=\"%s\"" \
					%(inf, each_country, check[index+1]["day"]))
	return True

def new_summary_periodic():
	r = requests.get(url=NEW_SUMMARY_URL) # SUMMARY_URL defined in libraries.py
	data = r.json()

	states_data = data["statewise"]

	app.logger.info("calling new summary")
	# app.logger.info(states_data)

	for each_state in states_data:
		## if state is total get summary
		active = int(each_state["active"])
		total = int(each_state["confirmed"])
		deaths = int(each_state["deaths"])
		recovered = int(each_state["recovered"])

		delta_total = int(each_state["deltaconfirmed"])
		delta_deaths = int(each_state["deltadeaths"])
		delta_recovered = int(each_state["deltarecovered"])
		delta_active = delta_total - delta_recovered - delta_deaths

		last_updated_time = each_state["lastupdatedtime"]

		state = each_state["state"]

		if each_state["state"] == "Total":
			check = exdb.getData("select * from summary")
			if not len(check):
				exdb.editData("insert into summary (total, deaths, recovered, active, delta_total, delta_deaths,\
				 delta_recovered, delta_active, last_updated_time) values (%d, %d, %d, %d, %d, %d, %d, %d, \"%s\")"\
				  %(total, deaths, recovered, active, delta_total, delta_deaths, delta_recovered, delta_active, last_updated_time))
			else:
				exdb.editData("update summary set total=%d, deaths=%d, recovered=%d, active=%d, last_updated_time=\"%s\",\
				 delta_total=%d, delta_deaths=%d, delta_recovered=%d, delta_active=%d" %(total, deaths, recovered, active,\
				  last_updated_time, delta_total, delta_deaths, delta_recovered, delta_active))	
		## for original states update statewise information
		else:
			check = exdb.getData("select * from statewise_latest where state=\"%s\"" %(state))
			if len(check):
				## update
				exdb.editData("update statewise_latest set total=%d, deaths=%d, recovered=%d, active=%d,\
				 last_updated_time=\"%s\", delta_total=%d, delta_deaths=%d, delta_recovered=%d, delta_active=%d\
				  where state=\"%s\"" %(total, deaths, recovered, active, last_updated_time, delta_total,\
				   delta_deaths, delta_recovered, delta_active, state))
			else:
				## insert
				exdb.editData("insert into statewise_latest (state, total, deaths, recovered, active, last_updated_time,\
				 delta_total, delta_deaths, delta_recovered, delta_active) values (\"%s\", %d, %d, %d, %d, \"%s\", %d, %d, %d, %d)"\
				  %(state, total, deaths, recovered, active, last_updated_time, delta_total, delta_deaths,\
				   delta_recovered, delta_active))
	
	return True

def patient_data_periodic():
	r = requests.get(url=PATIENT_DATA_URL) # PATIENT_DATA_URL defined in libraries.py
	data = r.json()["raw_data"]
	# latest_total = r.json()["data"]["summary"]["total"]
	app.logger.info("calling patient_data")
	for each in data:
		## patient data
		patient_id = int(each["patientnumber"])
		day = each["dateannounced"]
		try:
			if each["agebracket"]:
				if '-' in each["agebracket"]:
					age = int(int(each["agebracket"].split("-")[0])+int(each["agebracket"].split("-")[1])/2)
				else:
					age = int(each["agebracket"])
			else:
				age = 0
		except:
			age = 0

		gender = each["gender"]
		if gender == "F":
			gender = "Female"
		elif gender == "M":
			gender = "Male"
		else:
			gender = "Unidentified"

		city = each["detectedcity"]
		district = each["detecteddistrict"]
		state = each["detectedstate"]
		status = each["currentstatus"]
		try:
			notes = each["notes"]
		except:
			notes = ""
		if "contractedfromwhichpatientsuspected" in each:
			contracted_from = each["contractedfromwhichpatientsuspected"]
		else:
			contractedFrom = ""

		check_patient = exdb.getData("select * from patients where patient_id=%d" %(patient_id))
		if not len(check_patient):
			exdb.editData("insert into patients (patient_id, day, age, gender, city, district, state, status,\
			 notes, contracted_from) values (%d, \"%s\", %d, \"%s\", \"%s\", \"%s\", \"%s\", \"%s\", \"%s\", \"%s\")"\
			  %(patient_id, day, age, gender, city, district, state, status, notes, contracted_from))
		else:
			exdb.editData("update patients set day=\"%s\", age=%d, gender=\"%s\", city=\"%s\", district=\"%s\", state=\"%s\",\
			 status=\"%s\", notes=\"%s\", contracted_from=\"%s\" where patient_id=%d" %(day, age, gender, city, district, state,\
			  status, notes, contracted_from, patient_id))

	return True

@readings.route('/test', methods = ['GET'])
def test():
	return jsonify({"success": True, "message": "Data received Successfully! checking reload"})

@readings.route("/summary", methods=["GET"])
def summary():
	r = requests.get(url=SUMMARY_URL) # SUMMARY_URL defined in libraries.py
	data = r.json()["data"] 
	total = data["summary"]["total"]
	deaths = data["summary"]["deaths"]
	recovered = data["summary"]["discharged"]
	app.logger.info("calling summary")
	app.logger.info(data)
	for each_state in data["regional"]:
		check = exdb.getData("select * from statewise_latest where state=\"%s\"" %(each_state["loc"]))
		if len(check):
			## update
			exdb.editData("update statewise_latest set foreign_cases=%d, indian_cases=%d, deaths=%d,\
			 recovered=%d where state=\"%s\"" %(each_state["confirmedCasesForeign"], each_state["confirmedCasesIndian"],\
			  each_state["deaths"], each_state["discharged"], each_state["loc"]))
		else:
			## insert
			exdb.editData("insert into statewise_latest (state, foreign_cases, indian_cases, deaths, recovered) values\
			 (\"%s\", %d, %d, %d, %d)" %(each_state["loc"], each_state["confirmedCasesForeign"], each_state["confirmedCasesIndian"],\
			  each_state["deaths"], each_state["discharged"]))

	check = exdb.getData("select * from summary")
	if not len(check):
		exdb.editData("insert into summary (total, deaths, recovered) values (%d, %d, %d)" %(total, deaths, recovered))
	else:
		exdb.editData("update summary set total=%d, deaths=%d, recovered=%d" %(total, deaths, recovered))
	return jsonify({"success": True})

@readings.route("/new_summary", methods=["GET"])
def new_summary():
	r = requests.get(url=NEW_SUMMARY_URL) # SUMMARY_URL defined in libraries.py
	data = r.json()

	states_data = data["statewise"]

	app.logger.info("calling new summary")
	# app.logger.info(states_data)

	for each_state in states_data:
		## if state is total get summary
		active = int(each_state["active"])
		total = int(each_state["confirmed"])
		deaths = int(each_state["deaths"])
		recovered = int(each_state["recovered"])

		delta_total = int(each_state["deltaconfirmed"])
		delta_deaths = int(each_state["deltadeaths"])
		delta_recovered = int(each_state["deltarecovered"])
		delta_active = delta_total - delta_recovered - delta_deaths

		last_updated_time = each_state["lastupdatedtime"]

		state = each_state["state"]

		if each_state["state"] == "Total":
			check = exdb.getData("select * from summary")
			if not len(check):
				exdb.editData("insert into summary (total, deaths, recovered, active, delta_total, delta_deaths,\
				 delta_recovered, delta_active, last_updated_time) values (%d, %d, %d, %d, %d, %d, %d, %d, \"%s\")"\
				  %(total, deaths, recovered, active, delta_total, delta_deaths, delta_recovered, delta_active, last_updated_time))
			else:
				exdb.editData("update summary set total=%d, deaths=%d, recovered=%d, active=%d, last_updated_time=\"%s\",\
				 delta_total=%d, delta_deaths=%d, delta_recovered=%d, delta_active=%d" %(total, deaths, recovered, active,\
				  last_updated_time, delta_total, delta_deaths, delta_recovered, delta_active))	
		## for original states update statewise information
		else:
			check = exdb.getData("select * from statewise_latest where state=\"%s\"" %(state))
			if len(check):
				## update
				exdb.editData("update statewise_latest set total=%d, deaths=%d, recovered=%d, active=%d,\
				 last_updated_time=\"%s\", delta_total=%d, delta_deaths=%d, delta_recovered=%d, delta_active=%d\
				  where state=\"%s\"" %(total, deaths, recovered, active, last_updated_time, delta_total,\
				   delta_deaths, delta_recovered, delta_active, state))
			else:
				## insert
				exdb.editData("insert into statewise_latest (state, total, deaths, recovered, active, last_updated_time,\
				 delta_total, delta_deaths, delta_recovered, delta_active) values (\"%s\", %d, %d, %d, %d, \"%s\", %d, %d, %d, %d)"\
				  %(state, total, deaths, recovered, active, last_updated_time, delta_total, delta_deaths,\
				   delta_recovered, delta_active))
	
	return jsonify({"success": True})

@readings.route("/daily", methods=["GET"])
def daily():
	r = requests.get(url=DAILY_URL) # DAILY_URL defined in libraries.py
	data = r.json()["data"]
	for each_day in data:
		day = each_day["day"]
		total = each_day["summary"]["total"]
		deaths = each_day["summary"]["deaths"]
		recovered = each_day["summary"]["discharged"]
		active = total - recovered - deaths
		## converting day to timestamp
		dt = datetime(int(day.split("-")[0]), int(day.split("-")[1]), int(day.split("-")[2]))
		ts = (dt - datetime(1970, 1, 1)).total_seconds()
		check = exdb.getData("select * from second_daily where day=\"%s\"" %(day))
		if len(check) and day!= "2020-3-21":
			exdb.editData("update second_daily set total=%d, recovered=%d, deaths=%d, active=%d, timestamp=\"%s\" where day=\"%s\"" \
				%(total, recovered, deaths, active, ts, day))
		elif len(check)==0:
			exdb.editData("insert into second_daily (total, recovered, deaths, active, day, timestamp) values\
			 (%d, %d, %d, %d, \"%s\", \"%s\")" %(total, recovered, deaths, active, day, ts))
	return jsonify({"success": True})

@readings.route("/new_daily", methods=["GET"])
def new_daily():
	r = requests.get(url=NEW_SUMMARY_URL) # SUMMARY_URL defined in libraries.py
	data = r.json()
	app.logger.info("calling new daily")
	daily_data = data["cases_time_series"]
	each_country = "India"
	for each in daily_data:
		total = int(each["totalconfirmed"])
		recovered = int(each["totalrecovered"])
		deaths = int(each["totaldeceased"])
		active = total - deaths - recovered

		daily_total = int(each["dailyconfirmed"])
		daily_recovered = int(each["dailyrecovered"])
		daily_deaths = int(each["dailydeceased"])
		daily_active = daily_total - daily_deaths - daily_recovered

		date = each["date"] + "2020"

		ts = str(int((datetime.strptime(date, "%d %B %Y") - datetime(1970, 1, 1)).total_seconds()))

		check = exdb.getData("select * from third_daily where day=\"%s\"" %(date))
		if len(check):
			exdb.editData("update third_daily set total=%d, deaths=%d, recovered=%d, active=%d, daily_total=%d, daily_deaths=%d,\
			 daily_recovered=%d, daily_active=%d, timestamp=\"%s\" where day=\"%s\"" %(total, deaths, recovered, active, daily_total, daily_deaths,\
			  daily_recovered, daily_active, ts, date))
		else:
			exdb.editData("insert into third_daily (total, deaths, recovered, active, daily_total, daily_deaths, daily_recovered,\
			 daily_active, timestamp, day) values (%d, %d, %d, %d, %d, %d, %d, %d, \"%s\", \"%s\")" %(total, deaths, recovered, active, daily_total,\
			  daily_deaths, daily_recovered, daily_active, ts, date))

		## updating india data with covid19india data (this replaces JHU data for India)
		date_data = each["date"] + "2020"
		check = exdb.getData("select * from countrywise where country='India' and day=\"%s\"" %(date_data))
		if len(check):
			fatality_rate = (deaths*1.0/total)*100
			exdb.editData("update countrywise set count=%d, deaths=%d, fatality_rate=%f where country='India' and day=\"%s\"" %(total, deaths, fatality_rate, date_data))

			exdb.editData("update countrywise set mortality_rate=(deaths*1.0/%d) where country='India' and day=\"%s\"" %(POPULATION[each_country]/1000000, date_data))
	
	check = exdb.getData("select count, country, deaths, day from countrywise where country=\"%s\" order by timestamp asc" %(each_country))
	for index, i in enumerate(check):
		if index < (len(check)-1):
			if not index:
				exdb.editData("update countrywise set infection_rate=%f where country=\"%s\" and day=\"%s\"" \
					%(0.0, each_country, check[index]["day"]))
			if check[index]["count"]:
				inf = round(float(check[index+1]["count"])/float(check[index]["count"]), 2)					
				exdb.editData("update countrywise set infection_rate=%f where country=\"%s\" and day=\"%s\"" \
					%(inf, each_country, check[index+1]["day"]))
			else:
				inf = round(float(check[index+1]["count"]), 2)
				exdb.editData("update countrywise set infection_rate=%f where country=\"%s\" and day=\"%s\"" \
					%(inf, each_country, check[index+1]["day"]))

	return jsonify({"success": True})

@readings.route("/patient_data", methods=["GET"])
def patient_data():
	r = requests.get(url=PATIENT_DATA_URL) # PATIENT_DATA_URL defined in libraries.py
	data = r.json()["raw_data"]
	# latest_total = r.json()["data"]["summary"]["total"]
	app.logger.info("calling patient_data")
	for each in data:
		## patient data
		patient_id = int(each["patientnumber"])
		day = each["dateannounced"]
		try:
			if each["agebracket"]:
				if '-' in each["agebracket"]:
					age = int(int(each["agebracket"].split("-")[0])+int(each["agebracket"].split("-")[1])/2)
				else:
					age = int(each["agebracket"])
			else:
				age = 0
		except:
			age = 0

		gender = each["gender"]
		if gender == "F":
			gender = "Female"
		elif gender == "M":
			gender = "Male"
		else:
			gender = "Unidentified"

		city = each["detectedcity"]
		district = each["detecteddistrict"]
		state = each["detectedstate"]
		status = each["currentstatus"]
		try:
			notes = each["notes"]
		except:
			notes = ""
		if "contractedfromwhichpatientsuspected" in each:
			contracted_from = each["contractedfromwhichpatientsuspected"]
		else:
			contractedFrom = ""

		check_patient = exdb.getData("select * from patients where patient_id=%d" %(patient_id))
		if not len(check_patient):
			exdb.editData("insert into patients (patient_id, day, age, gender, city, district, state, status,\
			 notes, contracted_from) values (%d, \"%s\", %d, \"%s\", \"%s\", \"%s\", \"%s\", \"%s\", \"%s\", \"%s\")"\
			  %(patient_id, day, age, gender, city, district, state, status, notes, contracted_from))
		else:
			exdb.editData("update patients set day=\"%s\", age=%d, gender=\"%s\", city=\"%s\", district=\"%s\", state=\"%s\",\
			 status=\"%s\", notes=\"%s\", contracted_from=\"%s\" where patient_id=%d" %(day, age, gender, city, district, state,\
			  status, notes, contracted_from, patient_id))

	return jsonify({"success": True})

def all_countries_update():
	r = requests.get(url=ALL_COUNTRIES_CONFIRMED_URL, verify=False)
	total_confirmed = 0
	total_recovered = 0
	total_deaths = 0
	# print(r.text)
	import csv
	try:
		# For Python 3.0 and later
		from urllib.request import urlopen
	except ImportError:
		# Fall back to Python 2's urllib2
		from urllib2 import urlopen

	content = r.text
	rows = content.split("\n")
	full_data = {}
	for row in rows:
		items = row.split(",")
		if len(items)>10:
			if items[1] == "Country/Region":
				# for item in items[4:]:
				for row1 in rows:
					points = row1.split(",")
					if len(points)>10:
						if points[1] != "Country/Region":
							total_confirmed += int(points[-1])
						if points[1] in TOP_COUNTRIES:
							# print(points)
							if points[1] not in full_data:
								full_data[points[1]] = {}
							for i in range(len(points[4:])):
								if items[i+4] not in full_data[points[1]]:
									full_data[points[1]][items[i+4]] = int(points[i+4])
								else:
									full_data[points[1]][items[i+4]] += int(points[i+4])

				break
	for each_country in full_data.keys():
		for each_day in full_data[each_country].keys():
			day = datetime.strftime(datetime.strptime(each_day, '%m/%d/%y'), '%d %B %Y')
			count = full_data[each_country][each_day]
			check = exdb.getData("select * from countrywise where day=\"%s\" and country=\"%s\"" %(day, each_country))
			if len(check):
				exdb.editData("update countrywise set count=%d where day=\"%s\" and country=\"%s\"" %(count, day, items[1]))
			else:
				exdb.editData("insert into countrywise (day, country, count) values (\"%s\", \"%s\", %d)" %(day, each_country, count))

	r = requests.get(url=ALL_COUNTRIES_DEATHS_URL, verify=False)
	content = r.text
	# print(content)
	rows = content.split("\n")
	full_data = {}
	for row in rows:
		items = row.split(",")
		if len(items)>10:
			if items[1] == "Country/Region":
				# for item in items[4:]:
				for row1 in rows:
					points = row1.split(",")
					if len(points)>10:
						if points[1] != "Country/Region":
							total_deaths += int(points[-1])
						if points[1] in TOP_COUNTRIES:
							# print(points)
							if points[1] not in full_data:
								full_data[points[1]] = {}
							for i in range(len(points[4:])):
								if items[i+4] not in full_data[points[1]]:
									full_data[points[1]][items[i+4]] = int(points[i+4])
								else:
									full_data[points[1]][items[i+4]] += int(points[i+4])

				break
	# print("he", full_data)
	for each_country in full_data.keys():
		for each_day in full_data[each_country].keys():
			day = datetime.strftime(datetime.strptime(each_day, '%m/%d/%y'), '%d %B %Y')
			count = full_data[each_country][each_day]
			check = exdb.getData("select * from countrywise where day=\"%s\" and country=\"%s\"" %(day, each_country))
			if len(check):
				exdb.editData("update countrywise set deaths=%d where day=\"%s\" and country=\"%s\"" %(count, day, each_country))
	
	r = requests.get(url=ALL_COUNTRIES_RECOVERED_URL, verify=False)
	content = r.text
	# print(content)
	rows = content.split("\n")
	full_data = {}
	for row in rows:
		items = row.split(",")
		if len(items)>10:
			if items[1] == "Country/Region":
				# for item in items[4:]:
				for row1 in rows:
					points = row1.split(",")
					if len(points)>10:
						if points[1] != "Country/Region":
							total_recovered += int(points[-1])
				break
	counts = {}
	days = []
	infection = {}
	avgd= {}

	exdb.editData("update countrywise set fatality_rate=((deaths*1.0)/count)*100 where count>0")

	for each_country in TOP_COUNTRIES:
		exdb.editData("update countrywise set mortality_rate=(deaths*1.0/%d)" %(POPULATION[each_country]/1000000))

	check = exdb.getData("select * from countrywise")
	for i in check:
		date = str(i["day"])
		ts = str(int((datetime.strptime(date, "%d %B %Y") - datetime(1970, 1, 1)).total_seconds()))
		exdb.editData("update countrywise set timestamp=\"%s\" where country=\"%s\" and day=\"%s\"" %(ts, i["country"], i["day"]))
	
	for each_country in TOP_COUNTRIES:
		# print(each_country)
		check = exdb.getData("select count, country, deaths, day from countrywise where country=\"%s\" order by timestamp asc" %(each_country))
		for index, i in enumerate(check):
			if index < (len(check)-1):
				if not index:
					exdb.editData("update countrywise set infection_rate=%f where country=\"%s\" and day=\"%s\"" \
						%(0.0, each_country, check[index]["day"]))
				if check[index]["count"]:
					inf = round(float(check[index+1]["count"])/float(check[index]["count"]), 2)					
					exdb.editData("update countrywise set infection_rate=%f where country=\"%s\" and day=\"%s\"" \
						%(inf, each_country, check[index+1]["day"]))
				else:
					inf = round(float(check[index+1]["count"]), 2)
					exdb.editData("update countrywise set infection_rate=%f where country=\"%s\" and day=\"%s\"" \
						%(inf, each_country, check[index+1]["day"]))

	## global_summary
	total_active = total_confirmed - total_recovered - total_deaths
	check = exdb.getData("select * from global_summary")
	if not len(check):
		exdb.editData("insert into global_summary (confirmed, recovered, deaths, active) values (%d, %d, %d, %d)" %(total_confirmed, total_recovered, total_deaths, total_active))
	else:
		exdb.editData("update global_summary set confirmed=%d, recovered=%d, deaths=%d, active=%d" %(total_confirmed, total_recovered, total_deaths, total_active))
	return jsonify({"success": True})


def all_states_periodic():
	r = requests.get(url=ALL_STATES_URL, verify=False)
	content = r.json()
	data = content["states_daily"]
	for each in data:
		date = each["date"]
		status = each["status"]
		formatted_date = datetime.strftime((datetime.strptime(date, "%d-%b-%y")), "%d %B %Y")
		ts = str(int((datetime.strptime(date, "%d-%b-%y") - datetime(1970, 1, 1)).total_seconds()))
		print(date)
		for short_state in each.keys():
			if short_state in INDIAN_STATES.keys():
				print(each[short_state])
				try:
					count = int(each[short_state])
				except:
					count = 0
				state = INDIAN_STATES[short_state]
				if status == "Confirmed":
					check = exdb.getData("select * from statewise where state=\"%s\" and date=\"%s\"" %(state, formatted_date))
					if len(check):
						exdb.editData("update statewise set confirmed=%d where state=\"%s\" and date=\"%s\"" %(count, state, formatted_date))
					else:
						exdb.editData("insert into statewise (confirmed, state, date, timestamp) values (%d, \"%s\", \"%s\", \"%s\")" %(count, state, formatted_date, ts))
				if status == "Recovered":
					check = exdb.getData("select * from statewise where state=\"%s\" and date=\"%s\"" %(state, formatted_date))
					if len(check):
						exdb.editData("update statewise set recovered=%d where state=\"%s\" and date=\"%s\"" %(count, state, formatted_date))
					else:
						exdb.editData("insert into statewise (recovered, state, date, timestamp) values (%d, \"%s\", \"%s\", \"%s\")" %(count, state, formatted_date, ts))
				if status == "Deceased":
					check = exdb.getData("select * from statewise where state=\"%s\" and date=\"%s\"" %(state, formatted_date))
					if len(check):
						exdb.editData("update statewise set deaths=%d where state=\"%s\" and date=\"%s\"" %(count, state, formatted_date))
					else:
						exdb.editData("insert into statewise (deaths, state, date, timestamp) values (%d, \"%s\", \"%s\", \"%s\")" %(count, state, formatted_date, ts))

	check = exdb.getData("select distinct(date) as date, timestamp from statewise order by timestamp asc")
	for each_state in INDIAN_STATES.values():
		for index, each in enumerate(check):
			if index:
				cumu = exdb.getData("select sum(t1.confirmed) as cumu_confirmed, sum(t1.deaths) as cumu_deaths, sum(t1.recovered) as cumu_recovered from (select confirmed, deaths, recovered from statewise where state=\"%s\" order by timestamp asc limit %d) as t1" %(each_state, index))
				if len(cumu):
					cumu = cumu[0]
					exdb.getData("update statewise set cumu_confirmed=%d, cumu_recovered=%d, cumu_deaths=%d where state=\"%s\" and date=\"%s\"" %(cumu["cumu_confirmed"], cumu["cumu_recovered"], cumu["cumu_deaths"], each_state, each["date"]))

	exdb.editData("update statewise set fatality_rate=ROUND(((cumu_deaths*1.0)/cumu_confirmed)*100, 2) where cumu_confirmed>0")

	for each_country in INDIAN_STATES.values():
		print(each_country)
		print(float(INDIAN_STATES_POPULATION[each_country])/1000000.0)
		exdb.editData("update statewise set mortality_rate=ROUND((cumu_deaths*1.0/%f), 2)" %(float(INDIAN_STATES_POPULATION[each_country])/1000000.0))

	for each_country in INDIAN_STATES.values():
		# print(each_country)
		check = exdb.getData("select cumu_confirmed, state, cumu_deaths, date from statewise where state=\"%s\" order by timestamp asc" %(each_country))
		for index, i in enumerate(check):
			if index < (len(check)-1):
				if not index:
					exdb.editData("update statewise set infection_rate=%f where state=\"%s\" and date=\"%s\"" \
						%(0.0, each_country, check[index]["date"]))
				if check[index]["cumu_confirmed"]:
					inf = round(float(check[index+1]["cumu_confirmed"])/float(check[index]["cumu_confirmed"]), 2)					
					exdb.editData("update statewise set infection_rate=%f where state=\"%s\" and date=\"%s\"" \
						%(inf, each_country, check[index+1]["date"]))
				else:
					inf = round(float(check[index+1]["cumu_confirmed"]), 2)
					exdb.editData("update statewise set infection_rate=%f where state=\"%s\" and date=\"%s\"" \
						%(inf, each_country, check[index+1]["date"]))

	return True

@readings.route('/all_states', methods=["GET"])
def all_states():
	r = requests.get(url=ALL_STATES_URL, verify=False)
	content = r.json()
	data = content["states_daily"]
	for each in data:
		date = each["date"]
		status = each["status"]
		formatted_date = datetime.strftime((datetime.strptime(date, "%d-%b-%y")), "%d %B %Y")
		ts = str(int((datetime.strptime(date, "%d-%b-%y") - datetime(1970, 1, 1)).total_seconds()))
		print(date)
		for short_state in each.keys():
			if short_state in INDIAN_STATES.keys():
				print(each[short_state])
				try:
					count = int(each[short_state])
				except:
					count = 0
				state = INDIAN_STATES[short_state]
				if status == "Confirmed":
					check = exdb.getData("select * from statewise where state=\"%s\" and date=\"%s\"" %(state, formatted_date))
					if len(check):
						exdb.editData("update statewise set confirmed=%d where state=\"%s\" and date=\"%s\"" %(count, state, formatted_date))
					else:
						exdb.editData("insert into statewise (confirmed, state, date, timestamp) values (%d, \"%s\", \"%s\", \"%s\")" %(count, state, formatted_date, ts))
				if status == "Recovered":
					check = exdb.getData("select * from statewise where state=\"%s\" and date=\"%s\"" %(state, formatted_date))
					if len(check):
						exdb.editData("update statewise set recovered=%d where state=\"%s\" and date=\"%s\"" %(count, state, formatted_date))
					else:
						exdb.editData("insert into statewise (recovered, state, date, timestamp) values (%d, \"%s\", \"%s\", \"%s\")" %(count, state, formatted_date, ts))
				if status == "Deceased":
					check = exdb.getData("select * from statewise where state=\"%s\" and date=\"%s\"" %(state, formatted_date))
					if len(check):
						exdb.editData("update statewise set deaths=%d where state=\"%s\" and date=\"%s\"" %(count, state, formatted_date))
					else:
						exdb.editData("insert into statewise (deaths, state, date, timestamp) values (%d, \"%s\", \"%s\", \"%s\")" %(count, state, formatted_date, ts))

	check = exdb.getData("select distinct(date) as date, timestamp from statewise order by timestamp asc")
	for each_state in INDIAN_STATES.values():
		for index, each in enumerate(check):
			if index:
				cumu = exdb.getData("select sum(t1.confirmed) as cumu_confirmed, sum(t1.deaths) as cumu_deaths, sum(t1.recovered) as cumu_recovered from (select confirmed, deaths, recovered from statewise where state=\"%s\" order by timestamp asc limit %d) as t1" %(each_state, index))
				if len(cumu):
					cumu = cumu[0]
					exdb.getData("update statewise set cumu_confirmed=%d, cumu_recovered=%d, cumu_deaths=%d where state=\"%s\" and date=\"%s\"" %(cumu["cumu_confirmed"], cumu["cumu_recovered"], cumu["cumu_deaths"], each_state, each["date"]))

	exdb.editData("update statewise set fatality_rate=ROUND(((cumu_deaths*1.0)/cumu_confirmed)*100, 2) where cumu_confirmed>0")

	for each_country in INDIAN_STATES.values():
		print(each_country)
		print(float(INDIAN_STATES_POPULATION[each_country])/1000000.0)
		exdb.editData("update statewise set mortality_rate=ROUND((cumu_deaths*1.0/%f), 2)" %(float(INDIAN_STATES_POPULATION[each_country])/1000000.0))

	for each_country in INDIAN_STATES.values():
		# print(each_country)
		check = exdb.getData("select cumu_confirmed, state, cumu_deaths, date from statewise where state=\"%s\" order by timestamp asc" %(each_country))
		for index, i in enumerate(check):
			if index < (len(check)-1):
				if not index:
					exdb.editData("update statewise set infection_rate=%f where state=\"%s\" and date=\"%s\"" \
						%(0.0, each_country, check[index]["date"]))
				if check[index]["cumu_confirmed"]:
					inf = round(float(check[index+1]["cumu_confirmed"])/float(check[index]["cumu_confirmed"]), 2)					
					exdb.editData("update statewise set infection_rate=%f where state=\"%s\" and date=\"%s\"" \
						%(inf, each_country, check[index+1]["date"]))
				else:
					inf = round(float(check[index+1]["cumu_confirmed"]), 2)
					exdb.editData("update statewise set infection_rate=%f where state=\"%s\" and date=\"%s\"" \
						%(inf, each_country, check[index+1]["date"]))

	return jsonify({"success": True, "message": "Statewise Daily data"})

@readings.route('/all_countries', methods=["GET"])
def all_countries():
	r = requests.get(url=ALL_COUNTRIES_CONFIRMED_URL, verify=False)
	total_confirmed = 0
	total_recovered = 0
	total_deaths = 0
	# print(r.text)
	content = r.text
	rows = content.split("\n")
	full_data = {}
	for row in rows:
		items = row.split(",")
		if len(items)>10:
			if items[1] == "Country/Region":
				# for item in items[4:]:
				for row1 in rows:
					points = row1.split(",")
					if len(points)>10:
						if points[1] != "Country/Region":
							total_confirmed += int(points[-1])
						if points[1] in TOP_COUNTRIES:
							# print(points)
							if points[1] not in full_data:
								full_data[points[1]] = {}
							for i in range(len(points[4:])):
								if items[i+4] not in full_data[points[1]]:
									full_data[points[1]][items[i+4]] = int(points[i+4])
								else:
									full_data[points[1]][items[i+4]] += int(points[i+4])

				break
	for each_country in full_data.keys():
		for each_day in full_data[each_country].keys():
			day = datetime.strftime(datetime.strptime(each_day, '%m/%d/%y'), '%d %B %Y')
			count = full_data[each_country][each_day]
			check = exdb.getData("select * from countrywise where day=\"%s\" and country=\"%s\"" %(day, each_country))
			if len(check):
				exdb.editData("update countrywise set count=%d where day=\"%s\" and country=\"%s\"" %(count, day, items[1]))
			else:
				exdb.editData("insert into countrywise (day, country, count) values (\"%s\", \"%s\", %d)" %(day, each_country, count))

	r = requests.get(url=ALL_COUNTRIES_DEATHS_URL, verify=False)
	content = r.text
	# print(content)
	rows = content.split("\n")
	full_data = {}
	for row in rows:
		items = row.split(",")
		if len(items)>10:
			if items[1] == "Country/Region":
				# for item in items[4:]:
				for row1 in rows:
					points = row1.split(",")
					if len(points)>10:
						if points[1] != "Country/Region":
							total_deaths += int(points[-1])
						if points[1] in TOP_COUNTRIES:
							# print(points)
							if points[1] not in full_data:
								full_data[points[1]] = {}
							for i in range(len(points[4:])):
								if items[i+4] not in full_data[points[1]]:
									full_data[points[1]][items[i+4]] = int(points[i+4])
								else:
									full_data[points[1]][items[i+4]] += int(points[i+4])

				break
	# print("he", full_data)
	for each_country in full_data.keys():
		for each_day in full_data[each_country].keys():
			day = datetime.strftime(datetime.strptime(each_day, '%m/%d/%y'), '%d %B %Y')
			count = full_data[each_country][each_day]
			check = exdb.getData("select * from countrywise where day=\"%s\" and country=\"%s\"" %(day, each_country))
			if len(check):
				exdb.editData("update countrywise set deaths=%d where day=\"%s\" and country=\"%s\"" %(count, day, each_country))
	
	r = requests.get(url=ALL_COUNTRIES_RECOVERED_URL, verify=False)
	content = r.text
	# print(content)
	rows = content.split("\n")
	full_data = {}
	for row in rows:
		items = row.split(",")
		if len(items)>10:
			if items[1] == "Country/Region":
				# for item in items[4:]:
				for row1 in rows:
					points = row1.split(",")
					if len(points)>10:
						if points[1] != "Country/Region":
							total_recovered += int(points[-1])
				break
	counts = {}
	days = []
	infection = {}
	avgd= {}

	exdb.editData("update countrywise set fatality_rate=((deaths*1.0)/count)*100 where count>0")

	for each_country in TOP_COUNTRIES:
		exdb.editData("update countrywise set mortality_rate=(deaths*1.0/%d)" %(POPULATION[each_country]/1000000))

	check = exdb.getData("select * from countrywise")
	for i in check:
		date = str(i["day"])
		ts = str(int((datetime.strptime(date, "%d %B %Y") - datetime(1970, 1, 1)).total_seconds()))
		exdb.editData("update countrywise set timestamp=\"%s\" where country=\"%s\" and day=\"%s\"" %(ts, i["country"], i["day"]))
	
	for each_country in TOP_COUNTRIES:
		# print(each_country)
		check = exdb.getData("select count, country, deaths, day from countrywise where country=\"%s\" order by timestamp asc" %(each_country))
		for index, i in enumerate(check):
			if index < (len(check)-1):
				if not index:
					exdb.editData("update countrywise set infection_rate=%f where country=\"%s\" and day=\"%s\"" \
						%(0.0, each_country, check[index]["day"]))
				if check[index]["count"]:
					inf = round(float(check[index+1]["count"])/float(check[index]["count"]), 2)					
					exdb.editData("update countrywise set infection_rate=%f where country=\"%s\" and day=\"%s\"" \
						%(inf, each_country, check[index+1]["day"]))
				else:
					inf = round(float(check[index+1]["count"]), 2)
					exdb.editData("update countrywise set infection_rate=%f where country=\"%s\" and day=\"%s\"" \
						%(inf, each_country, check[index+1]["day"]))

	## global_summary
	total_active = total_confirmed - total_recovered - total_deaths
	check = exdb.getData("select * from global_summary")
	if not len(check):
		exdb.editData("insert into global_summary (confirmed, recovered, deaths, active) values (%d, %d, %d, %d)" %(total_confirmed, total_recovered, total_deaths, total_active))
	else:
		exdb.editData("update global_summary set confirmed=%d, recovered=%d, deaths=%d, active=%d" %(total_confirmed, total_recovered, total_deaths, total_active))
	return jsonify({"success": True})



######################### WorldMap ############################
###############################################################
def world_stats_update_periodic():
	# Get today's date 
	today = date.today() 
	  
	# Yesterday date 
	yesterday = today - timedelta(days = 1) 

	# Get filename from JHU CSSE Github repo
	yest_date = datetime.strftime(yesterday, "%m-%d-%Y")

	file_url = WORLD_DATA_BASE_URL + yest_date + ".csv"
	app.logger.info(file_url)

	r = requests.get(url=file_url, verify=False)
	# print(r.text)
	import csv
	try:
		# For Python 3.0 and later
		from urllib.request import urlopen
	except ImportError:
		# Fall back to Python 2's urllib2
		from urllib2 import urlopen

	content = r.text
	rows = content.split("\n")
	# print(rows)
	tags = rows[0].split(",")
	if tags[0] == "404: Not Found":
		return jsonify({"success": False, "message": "No file"})
		
	data = rows[1:]
	for i in data:
		i = i.replace(", ", "-")
		row = i.split(",")
		if len(row) == 12:
			last_updated_time = row[4]
			lat = row[5]
			lon = row[6]
			confirmed = int(row[7])
			deaths = int(row[8])
			recovered = int(row[9])
			active = int(row[10])
			place_name =  row[11].replace("'", "")
			try:
				place_name =  place_name.replace('"', "").encode('utf-8').decode('utf-8')
			except Exception as e:
				app.logger.info(str(e))
				continue

			check = exdb.getData("select * from world_stats where place=\"%s\"" %(place_name))
			if len(check):
				exdb.editData("update world_stats set confirmed=%d, active=%d, deaths=%d, recovered=%d, last_updated_time=\"%s\"\
				 where place=\"%s\"" %(confirmed, active, deaths, recovered, last_updated_time, place_name))
			else:
				exdb.editData("insert into world_stats (lat, lon, confirmed, active, deaths, recovered, place, last_updated_time) values \
					(\"%s\", \"%s\", %d, %d, %d, %d, \"%s\", \"%s\")" %(lat, lon, confirmed, active, deaths, recovered, place_name, last_updated_time))

	return jsonify({"success": True, "tags": tags})

@readings.route('/world_stats_update', methods=["GET"])
def world_stats_update():
	# Get today's date 
	today = date.today() 
	  
	# Yesterday date 
	yesterday = today - timedelta(days = 1) 

	# Get filename from JHU CSSE Github repo
	yest_date = datetime.strftime(yesterday, "%m-%d-%Y")

	file_url = WORLD_DATA_BASE_URL + yest_date + ".csv"
	app.logger.info(file_url)

	r = requests.get(url=file_url, verify=False)
	# print(r.text)
	import csv
	try:
		# For Python 3.0 and later
		from urllib.request import urlopen
	except ImportError:
		# Fall back to Python 2's urllib2
		from urllib2 import urlopen

	content = r.text
	rows = content.split("\n")
	# print(rows)
	tags = rows[0].split(",")
	if tags[0] == "404: Not Found":
		return jsonify({"success": False, "message": "No file"})

	data = rows[1:]
	for i in data:
		i = i.replace(", ", "-")
		row = i.split(",")
		if len(row) == 12:
			last_updated_time = row[4]
			lat = row[5]
			lon = row[6]
			confirmed = int(row[7])
			deaths = int(row[8])
			recovered = int(row[9])
			active = int(row[10])
			place_name =  row[11].replace("'", "")
			try:
				place_name =  place_name.replace('"', "").encode('utf-8').decode('utf-8')
			except Exception as e:
				app.logger.info(str(e))
				continue

			check = exdb.getData("select * from world_stats where place=\"%s\"" %(place_name))
			if len(check):
				exdb.editData("update world_stats set confirmed=%d, active=%d, deaths=%d, recovered=%d, last_updated_time=\"%s\"\
				 where place=\"%s\"" %(confirmed, active, deaths, recovered, last_updated_time, place_name))
			else:
				exdb.editData("insert into world_stats (lat, lon, confirmed, active, deaths, recovered, place, last_updated_time) values \
					(\"%s\", \"%s\", %d, %d, %d, %d, \"%s\", \"%s\")" %(lat, lon, confirmed, active, deaths, recovered, place_name, last_updated_time))

	return jsonify({"success": True, "tags": tags})

@readings.route('/world_stats', methods=["GET"])
def world_stats():
	data = exdb.getData("select id, lat, lon, place, confirmed, active, recovered, deaths, last_updated_time from world_stats")
	global_summary = exdb.getData("select * from global_summary")[0]
	statewise = exdb.getData("select distinct(district) as city_name from patients")
	for each_city in statewise:
		check = exdb.getData("select * from statelist where city_name=\"%s\"" %(each_city["city_name"]))
		if len(check):
			s = {}
			s["recovered"] = 0
			s["deaths"] = 0
			s["confirmed"] = exdb.getData("select count(*) as confirmed from patients where district=\"%s\" group by district" %(each_city["city_name"]))[0]["confirmed"]
			check1 = exdb.getData("select count(*) as recovered from patients where district=\"%s\" and status='Recovered' group by district" %(each_city["city_name"]))
			if len(check1):
				s["recovered"] = check1[0]["recovered"]
			check2 = exdb.getData("select count(*) as deaths from patients where district=\"%s\" and status='Deceased' group by district" %(each_city["city_name"]))
			if len(check2):
				s["deaths"] = check2[0]["deaths"]
			s["active"] = s["confirmed"] - s["recovered"] - s["deaths"]
			s["place"] = each_city["city_name"]
			s["lat"] = check[0]["latitude"].split()[0]
			s["lon"] = check[0]["longitude"].split()[0]
			data.append(s)
	print(data)

	statewise = exdb.getData("select * from statewise_latest")
	for index, state in enumerate(statewise):
		print(state)
		states_lat_lon = exdb.getData("select * from indian_states_lat_lon where state=\"%s\"" %(state["state"]))
		print(states_lat_lon)
		statewise[index]["lat"] = states_lat_lon[0]["lat"] 
		statewise[index]["lon"] = states_lat_lon[0]["lon"] 
		statewise[index]["confirmed"] = statewise[index]["total"]
		statewise[index]["place"] = states_lat_lon[0]["state"]
		data.append(statewise[index]) 
	return jsonify({"success": True, "data": data, "global_summary": global_summary})

@readings.route('/world_summary', methods=['GET'])
def world_summary():
	global_summary = exdb.getData("select * from global_summary")[0]
	return jsonify({"success": True, "message": "Global Summary", "global_summary": global_summary})

@readings.route('/us_data', methods=["GET"])
def us_data():
	data = exdb.getData("select id, lat, lon, place, confirmed, active, recovered, deaths, last_updated_time from world_stats where SUBSTRING_INDEX(place, '-', '-1')='US'")
	return jsonify({"success": True, "message": "US Data", "data": data})

@readings.route('/countrywise', methods=["GET"])
def countrywise():
	## for countrywise stats
	counts = {}
	days = []
	infection = {}
	fatality_rate = {}
	mortality_rate = {}
	avgd= {}
	for each_country in TOP_COUNTRIES:
		# print(each_country)
		check = exdb.getData("select count, country, deaths, infection_rate, fatality_rate, mortality_rate, day from countrywise where country=\"%s\" and count > 500 order by timestamp asc" %(each_country))
		for index, i in enumerate(check):
			if each_country in counts:
				counts[each_country].append(i["count"])
				infection[each_country].append(i["infection_rate"])
				fatality_rate[each_country].append(i["fatality_rate"])
				mortality_rate[each_country].append(i["mortality_rate"])
			else:
				counts[each_country] = [i["count"]]
				infection[each_country] = [i["infection_rate"]]
				fatality_rate[each_country] = [i["fatality_rate"]]
				mortality_rate[each_country] = [i["mortality_rate"]]
					
			if i["day"] not in days:
				days.append(i["day"])

	return jsonify({"success": True, "counts": counts, "days": days, "infection_rate": infection,\
	 "mortality_rate": mortality_rate, "fatality_rate": fatality_rate})


@readings.route('/statewise', methods=["GET", "POST"])
def statewise():
	## for statewise stats
	counts = {}
	days = {"days": []}
	infection = {}
	fatality_rate = {}
	mortality_rate = {}
	avgd= {}
	current_states = []
	if request.method == "POST":
		if request.json()["states"] == "":
			current_states = list(INDIAN_STATES.values())
		else:
			current_states = request.json()["states"].split(",")
	else:
		current_states = list(INDIAN_STATES.values())

	for each_country in current_states:
		# print(each_country)
		check = exdb.getData("select cumu_confirmed, state, cumu_deaths, infection_rate, fatality_rate, mortality_rate, date from statewise where state=\"%s\" and cumu_confirmed > 100 order by timestamp asc" %(each_country))
		for index, i in enumerate(check):
			if each_country in counts:
				counts[each_country].append(i["cumu_confirmed"])
				infection[each_country].append(i["infection_rate"])
				fatality_rate[each_country].append(i["fatality_rate"])
				mortality_rate[each_country].append(i["mortality_rate"])
			else:
				counts[each_country] = [i["cumu_confirmed"]]
				infection[each_country] = [i["infection_rate"]]
				fatality_rate[each_country] = [i["fatality_rate"]]
				mortality_rate[each_country] = [i["mortality_rate"]]
					
			if i["date"] not in days["days"]:
				days["days"].append(i["date"])

	check = exdb.getData("select distinct(state) as state, timestamp from statewise where cumu_confirmed>100")
	states = {"states": []}
	for each in check:
		if each["state"] not in states["states"] and each["state"] in current_states:
			states["states"].append(each["state"])

	return jsonify({"success": True, "counts": counts, "days": days["days"], "infection_rate": infection,\
		"mortality_rate": mortality_rate, "fatality_rate": fatality_rate, "states": states["states"]})

@readings.route('/get_summary', methods=["GET"])
def get_summary():
	statewise_latest = exdb.getData("select * from statewise_latest order by (total) desc")
	summary = exdb.getData("select * from summary")[0]
	summary["record_time"] = str(summary["record_time"])
	dashboard_graphs = exdb.getData("select * from third_daily order by timestamp asc")
	daily = exdb.getData("select * from third_daily order by timestamp asc")
	cumulative_confirmed = exdb.getData("SELECT total as count FROM third_daily ORDER BY timestamp asc")
	gender = exdb.getData("select gender, COUNT(*) as count from patients group by gender")
	today_date = datetime.now().strftime("%Y-%m-%d")
	yest_date = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
	bars = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
	age = {}
	for index, i in enumerate(bars):
		if index < len(bars)-1:
			age[str(bars[index]) + "-" + str(bars[index+1])] = exdb.getData("select count(*) as count from patients where age>%d and age<=%d" %(bars[index], bars[index+1]))[0]["count"]
	undefined = exdb.getData("select count(*) as count from patients where age=0")[0]["count"]
	total_diff = summary["delta_total"]
	active_diff = summary["delta_active"]
	deaths_diff = summary["delta_deaths"]
	recovered_diff = summary["delta_recovered"]

	today = date.today()
	firstday = date(2020, 1, 30)
	diff = today - firstday
	num_days = diff.days

	return jsonify({"success": True, "message": "readings", "statewise": statewise_latest, "daily": daily,\
	 "summary": summary, "gender": gender, "total_diff": total_diff, "active_diff": active_diff,\
	  "deaths_diff": deaths_diff, "recovered_diff": recovered_diff, "dashboard_graphs": dashboard_graphs,\
	   "age": age, "undefinedage": undefined, "num_days": num_days, "cumulative_confirmed": cumulative_confirmed})
