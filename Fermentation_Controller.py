import os
import time
import datetime
import RPi.GPIO as GPIO ## Import GPIO library
from tinydb import TinyDB, Query
import graphitesend

os.system('modprobe w1-gpio')
os.system('modprobe w1-therm')
abient_sensor = '/sys/bus/w1/devices/28-800000047828/w1_slave'
fermentation_sensor = '/sys/bus/w1/devices/28-8000000813ab/w1_slave'

HEATING_PIN=8
COOLING_PIN=9
GPIO.setmode(GPIO.BCM) ## Use board pin numbering
GPIO.setup(HEATING_PIN, GPIO.OUT) ## Setup GPIO Pin 8 to OUT
GPIO.setup(COOLING_PIN, GPIO.OUT) ## Setup GPIO Pin 9 to OUT

HEATING = "Heating"
HEATING_DELAYED = "Heating Delayed"
COOLING = "Cooling"
COOLING_DELAYED = "Cooling Delayed"
OFF = "Off"

FERMENTATION_ID = 1
AMBIENT_ID = 2
g = graphitesend.init(prefix="brewery", system_name='')


def read_temp_raw(sensor):
	f = open(sensor, 'r')
	lines = f.readlines()
	f.close()
	return lines

def HeatOn():
	print "Heating On"
	GPIO.output(HEATING_PIN, GPIO.LOW)

def HeatOff():
	print "Heating Off"
	GPIO.output(HEATING_PIN, GPIO.HIGH)

def CoolOn():
	print "Cooling On"
	GPIO.output(COOLING_PIN, GPIO.LOW)

def CoolOff():
	print "Cooling Off"
	GPIO.output(COOLING_PIN, GPIO.HIGH)


def read_temp(sensor):
	lines = read_temp_raw(sensor)
	while lines[0].strip()[-3:] != 'YES':
		time.sleep(0.2)
		lines = read_temp_raw()
	equals_pos = lines[1].find('t=')
	
	if equals_pos != -1:
		temp_string = lines[1][equals_pos+2:]
		temp_c = float(temp_string) / 1000.0
		temp_f = temp_c * 9.0 / 5.0 + 32.0
		return temp_c, temp_f

def cycle(db):

    Record = Query()
    dbRecords = db.search(Record.ID == FERMENTATION_ID)

    if(len(dbRecords) != 1):
        print "Unable to read on record from db"
        print db.all()
        exit(0)

    dbRecord = dbRecords[0]

    Variance = dbRecord["Variance"]
    State = dbRecord["State"]
    LastCoolOn = dbRecord["LastCoolOn"]
    LastHeatOn = dbRecord["LastHeatOn"]
    SetTemp_F = dbRecord["SetTemp_F"]
    CoolingDeplay = dbRecord["CoolingDelay"]
    HeatingDelay = dbRecord["HeatingDelay"]

    temp = read_temp(fermentation_sensor)
    temp_c = temp[0]
    temp_f = temp[1]
    current_time = time.time()

    print "[%s] %d" % (datetime.datetime.now(), temp_f)

    if temp_f > SetTemp_F:
        HeatOff()
        if temp_f > (SetTemp_F + Variance):
            if State == COOLING or current_time > (LastCoolOn + CoolingDeplay):
                CoolOn()
                State = COOLING
                LastCoolOn = current_time
            else:
                print "Cooling delay for another %s seconds" % ((LastCoolOn + CoolingDeplay) - current_time)
                State = COOLING_DELAYED
    elif temp_f < SetTemp_F:
        CoolOff()
        if temp_f < (SetTemp_F - Variance):
            if State == HEATING or time.time() > (LastHeatOn + HeatingDelay):
                HeatOn()
                State = HEATING
                LastHeatOn = current_time
            else:
                State = HEATING_DELAYED
    else:
        State = OFF

    db.update(
        {
            "State": State,
            "LastHeatOn": LastHeatOn,
            "LastCoolOn": LastCoolOn,
            "SetTemp_F": SetTemp_F,
            "Variance": Variance,
            "HeatingDelay": HeatingDelay,
            "CoolingDelay": CoolingDeplay,
            "LastUpdated": datetime.datetime.now().isoformat(),
            "Temp_F" : temp_f,
            "Temp_C" : temp_c
        }, Record.ID == FERMENTATION_ID
    )

    g.send("fermentation.temp.fahrenheit", temp_f)
    g.send("fermentation.temp.celsius", temp_c)
    if(State == OFF):
        g.send("fermentation.state.cool", 0)
        g.send("fermentation.state.heat", 0)
    elif State == COOLING:
        g.send("fermentation.state.cool", 1)
        g.send("fermentation.state.heat", 0)
    elif State == COOLING_DELAYED:
        g.send("fermentation.state.cool", 0.5)
        g.send("fermentation.state.heat", 0)
    elif State == HEATING:
        g.send("fermentation.state.cool", 0)
        g.send("fermentation.state.heat", 1)
    elif State == HEATING_DELAYED:
        g.send("fermentation.state.cool", 0)
        g.send("fermentation.state.heat", 0.5)


def InitializeRecord(db):
    Record = Query()
    records = db.search(Record.ID == FERMENTATION_ID)
    if len(records) > 0:
        record = records[0]

        if "LastHeatOn" in record:
            LastHeatOn = record["LastHeatOn"]
        else:
            LastHeatOn = time.time()

        if "LastCoolOn" in record:
            LastCoolOn = record["LastCoolOn"]
        else:
            LastCoolOn = time.time()

        if "SetTemp_F" in record:
            SetTemp_F = record["SetTemp_F"]
        else:
            SetTemp_F = 79

        if "Variance" in record:
            Variance = record["Variance"]
        else:
            Variance = 2

        if "HeatingDelay" in record:
            HeatingDelay = record["HeatingDelay"]
        else:
            HeatingDelay = 30

        if "CoolingDelay" in record:
            CoolingDelay = record["CoolingDelay"]
        else:
            CoolingDelay = 60


        db.update(
            {
                "State": State,
                "LastHeatOn": LastHeatOn,
                "LastCoolOn": LastCoolOn,
                "SetTemp_F": SetTemp_F,
                "Variance": Variance,
                "HeatingDelay": HeatingDelay,
                "CoolingDelay": CoolingDelay,
                "LastUpdated": datetime.datetime.now().isoformat(),
            }, Record.ID == FERMENTATION_ID
        )
    else:
        db.insert({
            "ID": FERMENTATION_ID,
            "State": State,
            "LastHeatOn": time.time(),
            "LastCoolOn": time.time(),
            "SetTemp_F": 68,
            "Variance": 2,
            "HeatingDelay": 30,
            "CoolingDelay": 60,
            "LastUpdated": datetime.datetime.now().isoformat()
        })

def InitializeAmbient(db):
    Record = Query()

    existing = db.search(Record.ID == AMBIENT_ID)
    if len(existing) > 0:
        db.update(
            {
              "LastUpdated": datetime.datetime.now().isoformat(),
            }, Record.ID == AMBIENT_ID
        )
    else:
        db.insert({
            "ID" : AMBIENT_ID,
            "LastUpdated": time.time()
        })

# Turn off the system when the app runs
CoolOff()
HeatOff()

db = TinyDB("/mnt/scripts/RasPiBrew2/db.json")
State = OFF
print("Initializing Records")
InitializeRecord(db)
InitializeAmbient(db)
print("Starting cycle")
while True:
    cycle(db)

    temp = read_temp(abient_sensor)
    Record = Query()
    dbRecords = db.search(Record.ID == AMBIENT_ID)
    dbRecord = dbRecords[0]

    dbRecord["LastUpdated"] = datetime.datetime.now().isoformat()
    dbRecord["Temp_F"] = temp[1]
    dbRecord["Temp_C"] = temp[0]

    g.send("ambient.temp.fahrenheit", temp[1])
    g.send("ambient.temp.celsius", temp[0])



    db.update(dbRecord, Record.ID == AMBIENT_ID)

    time.sleep(2)

