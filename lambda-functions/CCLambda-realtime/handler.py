import json
import boto3
import zeep
import io
import ast
import xmltodict


import os

from datetime import datetime
from zeep import Client
from zeep.transports import Transport
from requests.auth import HTTPBasicAuth
from requests import Session
from lxml import etree
from collections import Counter

def get_service(client, translation):
    service_binding = client.service._binding.name
    service_address = client.service._binding_options['address']
    return client.create_service(
        service_binding,
        service_address.replace(*translation, 1))

def update_dynamodb_table(table_name, linesDict, list):
    dynamodb = boto3.resource("dynamodb", region_name='eu-west-1')
    table = dynamodb.Table(table_name)

    with table.batch_writer() as batch:
        for line in list:
            lineInfo = linesDict[line]
            putItem = {
                    'lineCode' : lineInfo['lineCode'],
                    'directionId' : lineInfo['directionId']
            }
            for stop in lineInfo['arrivalTimes']:
                putItem[stop['stopCode']] = stop['arrivalTime']

            batch.put_item(
                Item=putItem
            )

def generateDynamoDBItems(data) :
    jsonData = json.loads(data)
    linesDictionary = {}
    linesList = []
    for line in jsonData:
        newStop = {}
        newStop['stopCode'] = line['stopCode']
        newStop['arrivalTime'] = line['arrivalTime']
        if line['lineCode'] in linesDictionary:
            existingLine = linesDictionary[line['lineCode']]
            existingLine['arrivalTimes'].append(newStop)
        else:
            linesList.append(line['lineCode'])
            arrivalTimes = []
            arrivalTimes.append(newStop)
            newLine = {}
            newLine['lineCode'] = line['lineCode']
            newLine['directionId'] = line['routeId'][-1:]
            newLine['arrivalTimes'] = arrivalTimes
            linesDictionary[line['lineCode']] = newLine

    update_dynamodb_table(os.environ['DYNAMODB_TABLE'], linesDictionary, linesList)



def getTMBData():
    session = Session()
    history = zeep.plugins.HistoryPlugin()
    session.verify = False
    session.auth = HTTPBasicAuth('upe00797', 'MbGi51')
    client = Client('https://dades.tmb.cat/secure/ws-ibus/IBusService?wsdl',
                    transport=Transport(session=session),
                    plugins=[history])

    service = get_service(client=client, translation=('10.200.133.31:8080', 'dades.tmb.cat'))

    result = service.getAllArrivalTimes('1')
    xmlresult = xmltodict.parse(etree.tounicode(history.last_received['envelope']))

    return json.dumps(xmlresult['env:Envelope']['env:Body']['ns1:getAllArrivalTimesResponse']['return'])

def ingest(event, context):
    print("Fixing")
    print("Starting new information retrieval from TMB services")
    print("Getting the information from the SOAP-WSDL services")
    #api call to TMB


    print("Updating the real-time data dynamoDB table")
    generateDynamoDBItems(getTMBData())
    #update_dynamodb_table(os.environ["DYNAMODB_TABLE"], generateDynamoDBItems(getTMBData()))


    body = {
        "message": "Daily ingest finished"
    }

    response = {
        "statusCode": 200,
        "body": json.dumps(body)
    }

    return response
