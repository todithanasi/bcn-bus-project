from django.db import models
import simplejson as json
from collections import Counter
from urllib.request import urlopen
import boto3
from boto3.dynamodb.conditions import Key, Attr
import os
import uuid
import logging
import time
import datetime
from django.utils import timezone
from decimal import Decimal
from dateutil import parser
from django.conf import settings
from time import gmtime, strftime


AWS_REGION = getattr(settings, "AWS_REGION", None)
REQUESTS_TABLE = getattr(settings, "REQUESTS_TABLE", None)
S3_TMB_DATA =  getattr(settings, "S3_TMB_DATA", None)
S3_CACHE =  getattr(settings, "S3_CACHE", None)
REAL_TIME_TABLE =  getattr(settings, "REAL_TIME_TABLE", None)
S3_URL =  getattr(settings, "S3_URL", None)


logger = logging.getLogger(__name__)

class Leads(models.Model):

    def get_leads(self, search_type, search_keyword):
        try:
            s3 = boto3.resource('s3', region_name=AWS_REGION)
        except Exception as e:
            logger.error(
                'Error connecting to s3'
            )
            return None
        if search_type == 'line':
            search_field = 'code'
        elif search_type == 'stop':
            search_field = 'name'

        try:
            list_file = s3.Object(S3_TMB_DATA, search_type + 's_list.json')
            file_content = list_file.get()['Body'].read().decode('utf-8')
        except Exception as e:
            logger.error(
                'File not found'
            )
            return None
        
        obj_list = json.loads(file_content)
        result = []
        for obj in obj_list:
            if search_keyword.lower() in obj[search_field].lower():
                result.append(obj)
        return result

    def get_stop(self, stop_code):
        try:
            s3 = boto3.resource('s3', region_name=AWS_REGION)
        except Exception as e:
            logger.error(
                'Error connecting to s3'
            )
            return None
        try:
            stop_file = s3.Object(S3_TMB_DATA, 'stops.json')
            file_content = stop_file.get()['Body'].read().decode('utf-8')
            stop = json.loads(file_content)[stop_code]
        except Exception as e:
            logger.error(
                'Stop ' + stop_code + ' not found '
            )
            return None
        stop['coming_buses'] = self.get_arrival_time(stop_code)
        stop['last_update_time'] = timezone.localtime()
        return stop

    def get_arrival_time(self, stop_code):
        try:
            dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
            table = dynamodb.Table(REAL_TIME_TABLE)
        except Exception as e:
            logger.error(
                'Error connecting to database table: ' + (e.fmt if hasattr(e, 'fmt') else '') + ','.join(e.args))
            return None
        response = table.scan(            
            FilterExpression=Attr(str(stop_code)).exists(),
            ExpressionAttributeNames={ "#stop": str(stop_code) },
            ProjectionExpression='lineCode, directionId, #stop'
        )
        lines = []
        try:
            s3 = boto3.resource('s3', region_name=AWS_REGION)
        except Exception as e:
            logger.error(
                'Error connecting to s3'
            )
            return None
        try:
            list_file = s3.Object(S3_TMB_DATA, 'lines_list.json')
            file_content = list_file.get()['Body'].read().decode('utf-8')
        except Exception as e:
            logger.error(
                'File lines_list.json not found'
            )
            return None       
        lines_list = json.loads(file_content)
        for item in response['Items']:
            time_in_m = int(round(int(item[str(stop_code)])/60+0.5))
            destination = self.get_destination(item['directionId'], self.get_name_by_code(item['lineCode'],lines_list))
            lines.append({'lineCode':item['lineCode'],'destination':destination,'time':time_in_m})
        return lines

    @staticmethod
    def get_destination(directionId, line_name):
        stops = line_name.split(' / ')
        if len(stops) == 1:
            return stops[0]
        return stops[int(directionId)]

    @staticmethod
    def get_name_by_code(line_code, lines_list):
        for line in lines_list:
            if line['code'] == str(line_code):
                return line['name']

    def get_line(self, line):
        try:
            s3 = boto3.resource('s3', region_name=AWS_REGION)
        except Exception as e:
            logger.error(
                'Error connecting to s3'
            )
            return None
        try:
            line_file = s3.Object(S3_TMB_DATA, 'lines/' + line +'.json')
            line_file_content = line_file.get()['Body'].read().decode('utf-8')
            stop_file = s3.Object(S3_TMB_DATA, 'stops.json')
            stop_file_content = stop_file.get()['Body'].read().decode('utf-8')
        except Exception as e:
            logger.error(
                'File not found'
            )
            return None   
        stops_data = json.loads(stop_file_content)  
        line_data = json.loads(line_file_content)
        directions = ['direction0','direction1']
        for direction in directions:
            for stop in line_data[direction]['stops']:
                stop_code = stop['code']
                other_lines = stops_data[stop_code]['lines']
                stop['other_lines'] = other_lines
        return line_data

    def push_user_request(self, query_type, data):
        try:
            dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
            table = dynamodb.Table(REQUESTS_TABLE)
        except Exception as e:
            logger.error(
                'Error connecting to database table: ' + (e.fmt if hasattr(e, 'fmt') else '') + ','.join(e.args))
            return 403
        try:
            if query_type is 'stop':
                response = table.put_item(
                    Item={
                        'id': str(uuid.uuid1()),
                        'Name': data['name'],
                        'Coordinates': data['coordinate']['ywgs84'] + ',' + data['coordinate']['xwgs84'],
                        'Querytime': str(int(time.time())),
                        'Type': 'stop',
                    },
                    ReturnValues='ALL_OLD',)
            else:
                response = table.put_item(
                    Item={
                        'id': str(uuid.uuid1()),
                        'Name': data['code'],
                        'Querytime': str(int(time.time())),
                        'Type': 'line',
                    },
                    ReturnValues='ALL_OLD',)
        except Exception as e:
            logger.error(
                'Error adding item to database: ' + (e.fmt if hasattr(e, 'fmt') else '') + ','.join(e.args))
            return 403
        status = response['ResponseMetadata']['HTTPStatusCode']

    def push_search_results(self, results, name):
        try:
            s3 = boto3.resource('s3', region_name=AWS_REGION)
            obj = s3.Object(S3_CACHE, name)
            obj.put(Body=results)
        except Exception as e:
            logger.error(
                'Error connecting to the s3 bucket: ' + (e.fmt if hasattr(e, 'fmt') else '') + ','.join(e.args)
            )
            return None

class UserRequests(models.Model):
    def getData(self, fromdate, todate):
        if fromdate is None and todate is None:
            filename = strftime("%Y-%m-%dT%H:%M", gmtime()) + ".json"
        elif fromdate is None:
            filename = todate + '.json'
        elif todate is None:
            filename = fromdate + '.json'
        else:
            filename = fromdate + '-' + todate + '.json'
        filename = 'requests/' + filename
        # connect to s3
        conn = boto3.resource('s3')
        # get s3 bucket
        bucket = conn.Bucket(S3_CACHE)
        key = filename
        objs = list(bucket.objects.filter(Prefix=key))
        # if file doesn't exist only then create the file
        if len(objs) <= 0:
            items = self.get_requests(fromdate, todate)
            conn.Object(S3_CACHE, filename).put(Body=json.dumps(items, indent=4))
        else:
            with urlopen(S3_URL + S3_CACHE + '/' + filename) as json_data:
                items = json.load(json_data)
        return items

    def mapData(self, items):
        coordinate_counter = Counter()
        coordinate_counter.update([item['Coordinates'] for item in items if item['Type'] == 'stop'])
        coordinate_freq = coordinate_counter.most_common(1000)
        map_data = {"mapdata": {"lat": float(1), "lng": float(1), "count": 0}}
        if len(coordinate_freq) > 0:
            map_data = []
            for item in coordinate_freq:
                coords = item[0].split(",")
                map_data.append({"lat": float(coords[0]), "lng": float(coords[1]), "count": item[1]})
            map_data = {
                "mapdata": map_data,
            }
        return map_data

    def chartData(self, items, type):
        stop_count = Counter()
        stop_count.update([item['Name'] for item in items if item['Type'] == type])
        stop_freq = stop_count.most_common(6)
        stop_data = {type:[],"callCounts": []}
        if len(stop_freq) > 0:
            labels, freq = zip(*stop_freq)
            stopNames = []
            callCounts = []
            for label in labels:
                stopNames.append(str(label))
            for f in freq:
                callCounts.append(f)
            stop_data = {
                type: stopNames,
                "callCounts": callCounts
            }
        return stop_data

    def get_requests(self, from_date, to_date):
        try:
            dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
            table = dynamodb.Table(REQUESTS_TABLE)
        except Exception as e:
            logger.error(
                'Error connecting to database table: ' + (e.fmt if hasattr(e, 'fmt') else '') + ','.join(e.args))
            return None
        expression_attribute_values = {}
        FilterExpression = []
        if from_date:
            from_date_parsed_init = time.strptime(from_date, '%Y-%m-%dT%H:%M')
            str_from_date = time.strftime('%Y-%m-%d %H:%M', from_date_parsed_init)
            from_date_parsed = str(parser.parse(str_from_date).timestamp())
            expression_attribute_values[':fd'] = from_date_parsed
            FilterExpression.append('Querytime >= :fd')
        if to_date:
            to_date_parsed_init = time.strptime(to_date, '%Y-%m-%dT%H:%M')
            str_to_date = time.strftime('%Y-%m-%d %H:%M', to_date_parsed_init)
            to_date_parsed = str(parser.parse(str_to_date).timestamp())
            expression_attribute_values[':td'] = to_date_parsed
            FilterExpression.append('Querytime < :td')
        if expression_attribute_values and FilterExpression:
            response = table.scan(
                FilterExpression=' and '.join(FilterExpression),
                ExpressionAttributeValues=expression_attribute_values,
            )
        else:
            response = table.scan(
                ReturnConsumedCapacity='TOTAL',
            )
        if response['ResponseMetadata']['HTTPStatusCode'] == 200:
            # print(response['Items'])
            return response['Items']
        logger.error('Unknown error retrieving items from database.')
        return None



