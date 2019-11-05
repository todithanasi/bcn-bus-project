import json
import boto3
import zeep
import xmltodict
import os

from datetime import datetime
from zeep import Client
from zeep.transports import Transport
from requests.auth import HTTPBasicAuth
from requests import Session
from lxml import etree

def get_service(client, translation):
    service_binding = client.service._binding.name
    service_address = client.service._binding_options['address']
    return client.create_service(
        service_binding,
        service_address.replace(*translation, 1))

def update_file(s3_bucket, file_path, newContent):
    try:
        s3 = boto3.resource('s3', region_name=os.environ['AWS_REGION'])
        s3_obj = s3.Object(s3_bucket, file_path)
        s3_obj.put(Body=newContent);

    except Exception as e:
        print("Error connecting to the s3 " + e)

    return None

def update_daily_data(s3_bucket, newData):
    jsonData = json.loads(newData)
    #Detailed information of each stop
    stops = {}
    #Brief resource for lines name and code
    linesList = []
    #Brief resource for stops name and code
    stopList = []
    stopLines = {}

    for line in jsonData:
        #Line data
        data = {}
        #Direction 0 of the line
        dir0 = {}
        #Direction 1 of the line
        dir1 = {}

        lineCode = line['line']['code']
        data['code'] = lineCode
        data['name'] = line['line']['name']

        simpleline = {}
        simpleline['code'] = lineCode
        simpleline['name'] = line['line']['name']
        #Appending simple information to lines list
        linesList.append(simpleline)

        #Gathering direction 0 information
        dir0['source'] = line['cartoroutes']['cartoroute'][0]['headsign']['source']
        dir0['destination'] = line['cartoroutes']['cartoroute'][0]['headsign']['destination']
        dir0stops = []


        #For each stop in direction 0, add it to the line list of stops, to the stops list and to the detailed stops file
        for stop in line['cartoroutes']['cartoroute'][0]['cartostops']['cartostop']:
            stop_data = {}
            stop_data['code'] = stop['code']
            stop_data['name'] = stop['name']
            ##appending the stop to the line
            dir0stops.append(stop_data)
            if stop['code'] in stops:
                ##If already exists in the stops file, we only update it.
                stops[stop['code']] = stop
                if lineCode not in stopLines[stop['code']]:
                    stopLines[stop['code']].append(lineCode)

            else:
                ##If it didn't exist in the stops list, we added to the stops list and to the detailed stops file
                simpleStop = {}
                simpleStop['code'] = stop['code']
                simpleStop['name'] = stop['name']
                stopList.append(simpleStop)
                stops[stop['code']] = stop
                stopLines[stop['code']] = []
                stopLines[stop['code']].append(lineCode)

        dir0['stops'] = dir0stops
        data['direction0'] = dir0


        #Gathering direction 1 information
        dir1['source'] = line['cartoroutes']['cartoroute'][1]['headsign']['source']
        dir1['destination'] = line['cartoroutes']['cartoroute'][1]['headsign']['destination']
        dir1stops = []

        #For each stop in direction 1, add it to the line list of stops, to the stops list and to the detailed stops file
        for stop in line['cartoroutes']['cartoroute'][1]['cartostops']['cartostop']:
            stop_data = {}
            stop_data['code'] = stop['code']
            stop_data['name'] = stop['name']
            ##appending the stop to the line
            dir1stops.append(stop_data)
            if stop['code'] in stops:
                ##If already exists in the stops file, we only update it.
                stops[stop['code']] = stop
                if (stop['code'] in stopLines):
                    stopLines[stop['code']].append(lineCode)
                else: 
                    stopLines[stop['code']] = []
                    stopLines[stop['code']].append(lineCode)
            else:
                ##If it didn't exist in the stops list, we added to the stops list and to the detailed stops file
                simpleStop = {}
                simpleStop['code'] = stop['code']
                simpleStop['name'] = stop['name']
                stopList.append(simpleStop)
                stops[stop['code']] = stop
                if (stop['code'] in stopLines):
                    stopLines[stop['code']].append(lineCode)
                else: 
                    stopLines[stop['code']] = []
                    stopLines[stop['code']].append(lineCode)

        dir1['stops'] = dir1stops
        data['direction1'] = dir1

        # Pushing or updating the line file in the s3 data lake
        update_file(s3_bucket, "lines/" + lineCode + ".json", json.dumps(data))

    for s in stops:
        stops[s]['lines'] = list(dict.fromkeys(stopLines[stops[s]['code']]))

    # Pushing or updating the stops file, and the dictionaries for stops and lists name and code.
    update_file(s3_bucket, "stops.json", json.dumps(stops))
    update_file(s3_bucket, "stops_list.json", json.dumps(stopList))
    update_file(s3_bucket, "lines_list.json", json.dumps(linesList))

def getTMBData():
    session = Session()
    history = zeep.plugins.HistoryPlugin()
    session.verify = False
    session.auth = HTTPBasicAuth('upe00797', 'MbGi51')

    client = Client('https://dades.tmb.cat/secure/ws-bus/LiniesBusService?wsdl',
                    transport=Transport(session=session),
                    plugins=[history])

    service = get_service(client=client, translation=('10.200.133.30:8080', 'dades.tmb.cat'))
    service.getBusLinesAndStops()

    xmlresult = xmltodict.parse(etree.tounicode(history.last_received['envelope']))

    return json.dumps(xmlresult['env:Envelope']['env:Body']['ns2:getBusLinesAndStopsResponse']['return'])

## Handler function
def ingest(event, context):
    print("Starting new information retrieval from TMB services")
    print("Getting the information from the SOAP-WSDL services")
    print("Updating the s3 bucket data lake")

    ##Updating daily data with the fetched data from TMB services
    update_daily_data(os.environ["S3_NAME"], getTMBData())

    body = {
        "message": "Daily ingest finished"
    }

    response = {
        "statusCode": 200,
        "body": json.dumps(body)
    }

    return response
