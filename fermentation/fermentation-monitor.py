import graphitesend
import RPi.GPIO as GPIO
import time
import logging
from logging.handlers import RotatingFileHandler


logger = logging.getLogger("fermentation-monitor")
# Rotate at 10Mb
hdlr = RotatingFileHandler('/var/log/fermentation-monitor/fermentation-monitor.log', maxBytes=10485760, backupCount=5)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)
logger.setLevel(logging.DEBUG)

GPIO.setmode(GPIO.BCM)

# init list with pin numbers
Heater = 17
HeaterFan = 27
Cooler = 22
CoolerFan = 10
State = "OFF"

LastCoolCycle = time.time()
CoolCycleDelay = 10 

pinList = [Heater,HeaterFan, Cooler, CoolerFan]

# loop through pins and set mode and state to 'low'

for i in pinList: 
    GPIO.setup(i, GPIO.OUT) 
    GPIO.output(i, GPIO.HIGH)

# time to sleep between operations in the main loop

SleepTimeL = 1

def adjust(onPins, offPins):
  GPIO.setmode(GPIO.BCM)
  for i in offPins:
    GPIO.setup(i, GPIO.OUT)
    GPIO.output(i, GPIO.HIGH)
  for i in onPins:
    GPIO.setup(i, GPIO.OUT)
    GPIO.output(i, GPIO.LOW)
# main loop
try:
  g = graphitesend.init(prefix="fermentation")
  while 1:
    tempfile = open("/sys/bus/w1/devices/28-0000075ed45c/w1_slave")
    thetext = tempfile.read()
    tempfile.close()
    tempdata = thetext.split("\n")[1].split(" ")[9]
    temperature = float(tempdata[2:])
    temperature = temperature / 1000
    f_temp = (temperature * 9)/5 + 32
    #print f_temp

    g.send("temp", f_temp)

    if f_temp > 75:
      g.send("cooling", 1)
      g.send("heating", 0)
      if State == "COOLING":
        continue
      now = time.time()
      if (LastCoolCycle + CoolCycleDelay) < now:
        adjust([Cooler, CoolerFan], [Heater, HeaterFan])
        LastCoolCycle = now
	State = "COOLING"  
      else:
        logger.info("Cooling Delayed for %s seconds" % ((LastCoolCycle + CoolCycleDelay) - now))
    elif f_temp < 70:
      g.send("heating", 1)
      g.send("cooling", 0)
      if State == "HEATING":
        continue
      adjust([Heater, HeaterFan], [Cooler, CoolerFan])
      State = "HEATING"
    else: 
      g.send("heating", 0)
      g.send("cooling", 0)
      GPIO.cleanup()
      State = "OFF"


    
    logger.debug("Temp %s (%s)" % (f_temp, State))

except KeyboardInterrupt:
  print "  Quit"

  # Reset GPIO settings
  GPIO.cleanup()


# find more information on this script at
# http://youtu.be/oaf_zQcrg7g
