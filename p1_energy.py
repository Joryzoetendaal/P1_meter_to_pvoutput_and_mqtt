#!/usr/bin/env python3
import sys
import time
import json
import requests
import serial
import os
import os.path
import datetime
import paho.mqtt.client as mqtt

#MQTT gegevens
mqtthost = '192.168.178.34'
mqttport = 1883
mqtttopic = 'grid'
mqttparameters = {'VoltageL1': 0,'PowerConsumption': 0,'PowerGenerated': 0,'EnergyConsumptionLow': 0,'EnergyConsumptionHigh': 0,'EnergyGeneratedLow': 0,'EnergyGeneratedHigh': 0,'CurrentL1': 0,'PowerL1': 0,'GasConsumption':0}

client = mqtt.Client("mqtt-energy-p1") # client ID "mqtt-test"
client.username_pw_set("homeassistant", {homeassistant-password})
client.connect(mqtthost, mqttport)

# Enable logging
DEBUG = 1

# PVOutput.org details
PVO_API='PVOutput.org API key'          # PVOutput.org API key
PVO_SYSID='System  ID'                                           # System  ID
PVO_URL = 'http://pvoutput.org/service/r2/addstatus.jsp'    # PV output url
# --------------------

# Open Weather Map details
units       = 'metric'
latitude    = 'latitude'
longitude   = 'longitude'
app_id      = 'app_id'
# --------------------

#Upload alleen op bepaalde minuten
now = datetime.datetime.now()
minute = int(now.minute)
hour = int(now.hour)

#-------------------logging-------------------#
def logging (logdata):
    Date = time.strftime('%Y_%m_%d')
    Time = time.strftime('%R')
    logfile_name = "/home/pi/logfiles/" + str(Date) + "_logfile.txt"
    f = open(logfile_name, 'a')
    f.write("%s %s %s\r\n" % (Date,Time,logdata))
    f.close
    return

#-------------------get_temperature-------------------#
def get_temperature():
  url = 'https://api.openweathermap.org/data/2.5/weather?units=%s&lat=%s&lon=%s&appid=%s' % (units,latitude,longitude,app_id)
  
  # Get the data from open weather map.
  response = requests.get(url)

  if (response.status_code == 200):
    json_res = response.json()
    Temperature = float(json_res["main"]["temp"])
    #print(json.dumps(json_res,indent=4))
    #Round temperature to nearest 0.5 otherwise PVOutput graph is very shaky
    Temperature= round(Temperature * 2) / 2
  return (Temperature)
#-----------------------------------------------------#

#------------------post_add_status--------------------#
def post_add_status(): # may raise exceptions
    if minute==0 or minute==5 or minute==10 or minute==15 or minute==20 or minute==25 or minute==30 or minute==35 or minute==40 or minute==45 or minute==50 or minute==55:
        Date = time.strftime('%Y%m%d')
        Time = time.strftime('%R')
        Temperature = get_temperature()

        print ("d:", Date)
        print ("t:", Time)
        print ("v1:", EnergyGenerated,"Watt Hours")
        print ("v2:",PowerGenerated,"Watts")
        print ("v3:",EnergyConsumptionToday,"Watt Hours") 
        print ("v4:", PowerConsumption,"Watts")
        print ("v5:", Temperature,"Celcius")
        print ("v6:", ActiveVoltageL1,"Volts")

        TempLog = "EnergyGenerated: " + str(EnergyGenerated) +  " WH"
        logging(TempLog)
        TempLog = "PowerGenerated: " + str(PowerGenerated) +  " Watts"
        logging(TempLog)
        TempLog = "EnergyConsumptionToday: " + str(EnergyConsumptionToday) +  " WH"
        logging(TempLog)
        TempLog = "PowerConsumption: " + str(PowerConsumption) +  " Watts"
        logging(TempLog)
        TempLog = "Temperature: " + str(Temperature) +  " Temp"
        logging(TempLog)
        TempLog = "ActiveVoltageL1: " + str(ActiveVoltageL1) +  " Voltage"
        logging(TempLog)

        TempLog = "EnergyGeneratedToday: " + str(EnergyGeneratedToday) +  " WH"
        logging(TempLog)
        TempLog = "PowerGenerated: " + str(PowerGenerated) +  " Watts"
        logging(TempLog)
        TempLog = "GasConsumptionToday: " + str(GasConsumptionToday) +  " dm3"
        logging(TempLog)
        PowerUsedOfSolarWH = float(EnergyGenerated) - float(EnergyGeneratedToday)
        TempLog = "PowerUsedDirectOutOfSolar: " + str(PowerUsedOfSolarWH) +  " WH"
        logging(TempLog)
        TotalEnergyUsed = float(EnergyConsumptionToday) + float(PowerUsedOfSolarWH)   
        TempLog = "TotalEnergyUsed: " + str(TotalEnergyUsed) +  " WH"
        logging(TempLog)
    
        url = PVO_URL
        headers = {
            'X-Pvoutput-SystemId': str(PVO_SYSID),
            'X-Pvoutput-Apikey': str(PVO_API)
        }
        params = {
            'd': Date,
            't': Time,
            'v1': EnergyGenerated,
            'v2': PowerGenerated,
            'v3': EnergyConsumptionToday,
            'v4': PowerConsumption,
            'v5': Temperature,
            'v6': ActiveVoltageL1
        }
        logging("Posting data to PV Output")
        resp = requests.post(url, headers=headers, data=params, timeout=10)
        
        TempLog = "ResponseCode of PV Output: " + str(resp.status_code)
        logging(TempLog)
    else:
	    print('No need to upload to PVOutput...')  
    return
#-----------------------------------------------------#


#-----------------read_p1_meter_data------------------#
def read_p1_meter_data():
    #Set COM port config
    ser = serial.Serial()
    ser.baudrate = 115200
    ser.bytesize=serial.SEVENBITS
    ser.parity=serial.PARITY_EVEN
    ser.stopbits=serial.STOPBITS_ONE
    ser.xonxoff=0
    ser.rtscts=0
    ser.timeout=20
    ser.port="/dev/ttyUSB0"

    global EnergyConsumption 
    global PowerConsumption
    global EnergyGenerated
    global PowerGenerated
    global GasConsumption
    global ActiveVoltageL1

    EnergyConsumption = 0
    EnergyGenerated = 0
    PowerConsumption = 0
    PowerGenerated = 0
    GasConsumption = 0
    ActiveVoltageL1 = 0
    #Open COM port
    try:
        ser.open()
     #Als het niet lukt, wacht dan 5 secs en doe het nog een keer...
    except:
        return

    # Initialize
    # stack is the array where the p1 data is stored
    p1_counter=0
    stack=[]

    p1_meter_name = '/XMX5LGBBLB2415134'

    while p1_counter < 20:
        p1_line=''
        #Read 1 line
        try:
            p1_raw = ser.readline()
        except:
            sys.exit ("Serial port %s can not be read. Program stopped." % ser.name )      
        #p1_str=str(p1_raw)             #for python 2
        p1_str=str(p1_raw, "utf-8")     #for python 3

        p1_line=p1_str.strip()

        stack.append(p1_line)
        # uncomment the next line to see the data in the console
        print (p1_line)

        p1_counter = p1_counter +1
        if (stack[0][0:18] != p1_meter_name):
            p1_counter = 0
            stack.clear()

    #Initialize
    # stack_counter is mijn tellertje voor de 20 weer door te lopen. Waarschijnlijk mag ik die p1_counter ook gebruiken
    stack_counter=0

    while stack_counter < 20:
        # Off Peak rate, used Current 1-0:1.8.1
        if stack[stack_counter][0:9] == "1-0:1.8.1":
            if (DEBUG):
                print ("Used Power in Off-Peak     ", int(float(stack[stack_counter][10:20])*1000),"Watt Hour")
            EnergyConsumption = int(float(stack[stack_counter][10:20])*1000)
            mqttparameters['EnergyConsumptionLow'] = float(str(stack[stack_counter][10:20]).lstrip("0"))
        # Peak rate, used Current 1-0:1.8.2
        elif stack[stack_counter][0:9] == "1-0:1.8.2":
            if (DEBUG):
                print ("Used Power in Peak     ", int(float(stack[stack_counter][10:20])*1000),"Watt Hour")
            EnergyConsumption = EnergyConsumption + int(float(stack[stack_counter][10:20])*1000)
            mqttparameters['EnergyConsumptionHigh'] = float(str(stack[stack_counter][10:20]).lstrip("0"))
        # Off peak rate, Returned Power 1-0:2.8.1
        elif stack[stack_counter][0:9] == "1-0:2.8.1":
            if (DEBUG):
                print ("Returned Power in Off-Peak   ", int(float(stack[stack_counter][10:20])*1000),"  Watt Hour")
            EnergyGenerated = int(float(stack[stack_counter][10:20])*1000)
            mqttparameters['EnergyGeneratedLow'] = float(stack[stack_counter][10:20])
        # Peak rate, Returned Power 1-0:2.8.2
        elif stack[stack_counter][0:9] == "1-0:2.8.2":
            if (DEBUG):
                print ("Returned Power in Peak ", int(float(stack[stack_counter][10:20])*1000),"Watt Hour")
            EnergyGenerated = EnergyGenerated + int(float(stack[stack_counter][10:20])*1000)
            mqttparameters['EnergyGeneratedHigh'] = float(stack[stack_counter][10:20])
        # Current power draw: 1-0:1.7.0
        elif stack[stack_counter][0:9] == "1-0:1.7.0":
            if (DEBUG):
                print ("Current power draw    ", int(float(stack[stack_counter][10:16])*1000), " W")
            PowerConsumption = int(float(stack[stack_counter][10:16])*1000)
            mqttparameters['PowerConsumption'] = int(float(stack[stack_counter][10:16])*1000)
        # Current power returned: 1-0:1.7.0
        elif stack[stack_counter][0:9] == "1-0:2.7.0":
            if (DEBUG):
                print ("Current power returned  ", int(float(stack[stack_counter][10:16])*1000), " W")
            PowerGenerated = float(stack[stack_counter][10:16])*1000
            mqttparameters['PowerGenerated'] = int(float(stack[stack_counter][10:16])*1000)
        elif stack[stack_counter][0:10] == "1-0:32.7.0":
            if (DEBUG):
                print ("Voltage L1  ",    float(stack[stack_counter][11:16]), " V")
            ActiveVoltageL1 = float(stack[stack_counter][11:16])
            mqttparameters['VoltageL1'] = float(stack[stack_counter][11:16])
          #Stroom uitgeschakeld omdat berekenen via spanning en vermogen gedetailleerder is.
        elif stack[stack_counter][0:10] == "1-0:31.7.0":
            mqttparameters['CurrentL1'] = float(stack[stack_counter][11:14])
        # Gasmeter: 0-1:24.3.0
        elif stack[stack_counter][0:10] == "0-1:24.3.0":
            if (DEBUG):
                print ("Gas                     ", int(float(stack[stack_counter+1][1:10])*1000), " dm3")
            GasConsumption = int(float(stack[stack_counter+1][1:10])*1000)
            mqttparameters['GasConsumption'] = float(stack[stack_counter][1:10])
        else:
            pass
        stack_counter = stack_counter +1

    #Bereken de stroom aan de hand van vermogen en prik (alleen als de waarde ongelijk aan 0 is)
    if (mqttparameters['VoltageL1'] != 0): 
    	mqttparameters['PowerL1'] = round(float(mqttparameters['CurrentL1'] * mqttparameters['VoltageL1']),3) 
    
    #Close port and show status
    try:
        ser.close()
    except:
        sys.exit ("Oops %s. Program stopped." % ser.name )     
    return 
    
#-------send_mqtt_data_to_homeassistant---------#   
def send_mqtt_data_to_homeassistant():
    mqttpayload = json.dumps(mqttparameters) #Zet Python list om naar correcte JSON
    client.publish(mqtttopic,mqttpayload)  
    print(str(mqttparameters)) #Voor Debug stuur MQTT bericht naar log file
    return

#-------------end_of_day_report----------------#    
def end_of_day_report():
    #Schrijf de eindstand van vandaag om 23:59 weg in een bestand.
    if (hour==23 and minute==59): 
        logging("whoooo daily usage")
        logging("Storing daily usage")
        verbruik=open('/home/pi/settings/verbruik', 'a+')
        verbruik.write("Day : %s \n" % int(time.strftime("%-d", time.localtime())));
        verbruik.write("EnergyGenerated   : %s WH \n" % EnergyGenerated);
        verbruik.write("EnergyConsumption  : %s WH\n" % EnergyConsumptionToday);  
        verbruik.write("EnergyGenerated     : %s WH\n" % str(EnergyGeneratedToday));
        verbruik.write("PowerDirectOutSolar: %s WH\n" %  str(float(EnergyGenerated) - float(EnergyGeneratedToday)));
        verbruik.write("TotalEnergyUsed    : %s WH\n" %  str(float(EnergyConsumptionToday) + float(EnergyGenerated) - float(EnergyGeneratedToday)));
        verbruik.write("GasConsumption     : %s dm3\n" % GasConsumptionToday);
        verbruik.close()
    return

#-------------read_daily_stored_data----------------#
def read_daily_stored_data():

    global EnergyConsumptionToday
    global EnergyGeneratedToday
    global GasConsumptionToday
    global PowerUsedOfSolarWH
    Today = int(time.strftime("%-d", time.localtime()))
    if os.path.isfile('/home/pi/settings/daily_energy.json'):
        print ("File exist")
    else:
        print ("File not exist create file with json object")
        with open('/home/pi/settings/daily_energy.json', 'w') as json_new_file:
            my_details = {
                "day": Today,
                "energy": EnergyConsumption,
                "energyReturned" : EnergyGenerated,
                "gas" : GasConsumption
            }
            json.dump(my_details, json_new_file)
    with open('/home/pi/settings/daily_energy.json', 'r+') as json_file:
        DailyEnergy = json.load(json_file)
        # uncomment to print the readed json dump
        # print (json.dumps(DailyEnergy, indent=4))
        ReadStoredDay               = int(DailyEnergy["day"])
        ReadStoredEnergy            = int(DailyEnergy["energy"])
        ReadStoredEnergyReturned    = int(DailyEnergy["energyReturned"])
        ReadStoredGas               = int(DailyEnergy["gas"])
        #print(ReadStoredDay , ReadStoredEnergy)
        if (ReadStoredDay != Today): 
            EnergyConsumptionToday  = EnergyConsumption - ReadStoredEnergy 
            EnergyGeneratedToday     = EnergyGenerated    - ReadStoredEnergyReturned
            GasConsumptionToday     = GasConsumption    - ReadStoredGas

            logging("Open daily energy file")
            open("daily_energy.json", "w").close()
            json_file.seek(0)
            my_details = {
                "day": Today,
                "energy": EnergyConsumption,
                "EnergyGenerated" : EnergyGenerated,
                "gas" : GasConsumption
            }
            json.dump(my_details, json_file)
            logging(my_details)
            json_file.truncate()
            EnergyConsumptionToday  = 0 
            EnergyGeneratedToday     = 0
            GasConsumptionToday     = 0
        else:
            EnergyConsumptionToday  = EnergyConsumption - ReadStoredEnergy 
            EnergyGeneratedToday     = EnergyGenerated    - ReadStoredEnergyReturned
            GasConsumptionToday     = GasConsumption    - ReadStoredGas
        #print("read_stored_data:",EnergyConsumptionToday)

    return

#run program
read_p1_meter_data();
read_daily_stored_data();
send_mqtt_data_to_homeassistant();
post_add_status();
end_of_day_report();
