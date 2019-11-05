from django.shortcuts import render
from .models import Leads
from .models import UserRequests
from collections import Counter
from urllib.request import urlopen
import boto3
import time
import simplejson as json
from time import gmtime, strftime
from django.conf import settings
import os

S3_CACHE =  getattr(settings, "S3_CACHE", None)
S3_URL =  getattr(settings, "S3_URL", None)
AWS_REGION = getattr(settings, "AWS_REGION", None)

# REQUESTS_BUCKET_URL = getattr(settings, "REQUESTS_BUCKET_URL", None)

def home(request):
    return render(request, 'index.html')

def search(request):
	stop = request.GET.get('stop')
	line = request.GET.get('line')
	lead = Leads()

	#Search for both line and stop (invalid)
	if stop and line:
		return render(request, 'notfound.html')

	#Search for stop
	if stop:
		stop_data = lead.get_stop(stop)
		if stop_data is None:
			return render(request, 'notfound.html')
		lead.push_user_request('stop', stop_data)
		return render(request, 'result.html', {'stop': stop_data})

	if line:
		line_data = lead.get_line(line)
		if line_data is None:
			return render(request, 'notfound.html')
		lead.push_user_request('line', line_data)
		return render(request, 'result.html', {'line': line_data})	

	search_type = request.GET.get('searchType')
	search_keyword = request.GET.get('searchKeyword')
	if search_type and search_keyword:
		items = lead.get_leads(search_type, search_keyword)
		file_name = search_type + "/" + search_keyword.lower() + ".json"
		lead.push_search_results(json.dumps(items), file_name)
		file_name = S3_URL + S3_CACHE + '/' + str(file_name) 
		return render(request, 'result.html', {'items': items, 'search_type': search_type, 'result_file_name': file_name})
	else:
		return render(request, 'search.html')


def dashboard(request):
    fromdate = request.GET.get('fromdate')
    todate = request.GET.get('todate')
    userrequests = UserRequests()
    items = userrequests.getData(fromdate, todate)
    map_data = userrequests.mapData(items)
    stop_data = userrequests.chartData(items, 'stop')
    line_data = userrequests.chartData(items, 'line')
    return render(request, 'dashboard.html', {"stopdata": stop_data, "linedata": line_data, "mapcoord": map_data})

