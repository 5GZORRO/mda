from typing import List
from fastapi import FastAPI, Query, Request, Header
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import random, requests, os

import urllib.parse as urlparse
from urllib.parse import parse_qs

MIN_AVAILABILITY=0.90
MAX_AVAILABILITY=0.99

initial_value = 0.95
time_now = datetime.now()
next_time_change = time_now + timedelta(hours = 1)

app = FastAPI()

def get_interval_datetimes(start, end, step_time, step_unit):
    datetimes = []
    if end is None:
        datetimes.append(start)
        return datetimes
    curr_date = start
    while curr_date <= end:
        datetimes.append(curr_date)
        if step_unit  == 's':
            curr_date = curr_date + relativedelta(seconds=step_time)
        elif step_unit  == 'm':
            curr_date = curr_date + relativedelta(minutes=step_time)
        elif step_unit  == 'h':
            curr_date = curr_date + relativedelta(hours=step_time)
        elif step_unit  == 'd':
            curr_date = curr_date + relativedelta(days=step_time)
        elif step_unit  == 'M':
            curr_date = curr_date + relativedelta(months=step_time)
        elif step_unit  == 'y':
            curr_date = curr_date + relativedelta(years=step_time)
    return datetimes

def generate_response():
    # Random distribution with weights
    request_types=['201', '500']
    option = random.choices(request_types, weights=[0.9, 0.09], k=1)
    if option == ['201']:
        st = 0
    else:
        st = 1
    return request_types[st]

def generate_availability():

    global time_now
    global next_time_change
    global initial_value
    
    if next_time_change < datetime.now():

        if initial_value >= 0.99:
            initial_value = 0.98

        elif initial_value <= 0.91:
            initial_value = 0.92

        else:
            random_value = round(random.uniform(float(MIN_AVAILABILITY), float(MAX_AVAILABILITY)), 2)

            if random_value > 0.95:
                initial_value = initial_value + 0.01

            else:
                initial_value = initial_value - 0.01

        next_time_change = next_time_change + timedelta(hours = 1)

        return initial_value
    
    else:
        return initial_value

# ----------------------------------------------------------------#

@app.get("/osm/api/v1/query")
async def query(time: datetime, query: str, X_Gravitee_Api_Key: str = Header(None)):
    # /query_range?query=up&
    #              time=2015-07-01T20:10:30.781Z

    if X_Gravitee_Api_Key == None:
        return JSONResponse(status_code=404, content={"status": "Error", "message": "Header 'X-Gravitee-Api-Key' required."})
    if query == None:
        return JSONResponse(status_code=404, content={"status": "Error", "message": "Query required."})
    
    # Random response
    if generate_response() == '500':
      return JSONResponse(status_code=500, content={"status": "Error", "message": "Faild to connect to OSM."})

    response = {
        "status": "success",
        "data": {
            "resultType" : "matrix",
            "result" : []
        }
    }
    for i in range(2):
      json_metric = {
          "metric": {
              "__name__" : query,
              "job" : "mon_exporter",
              "instance" : "mon:8000",
              "ns_id": str(i)+"5cce067-4818-4afc-b0f8-0e4a1babf753",
              "ns_name": "test"+str(i)+"_instance",
              "project_id": str(i)+"b0d7475-319f-48ce-a216-92b85f7800a8",
              "vdu_name": "test-"+str(i)+"-mgmtVM-0",
              "vnf_member_index": str(i)
          }                    
      }
      
      json_metric_ran = {
          "metric": {
              "__name__" : query,
              "job" : "amarisoft",
              "instance" : "0.0.0.0:8000",
              "cell_id": str(i)+"5cce067-4818-4afc-b0f8-0e4a1babf753"
          }
      }
    
      if query == "osm_requests":
          json_metric['value'] = [datetime.timestamp(time), str(round(random.uniform(0,1),2))]
          response['data']['result'].append(json_metric)
      
      elif query == "availability":
          json_metric['value'] = [datetime.timestamp(time), str(round(generate_availability(), 2))]
          response['data']['result'].append(json_metric)
          
      elif query == "up":
          json_metric['value'] = [datetime.timestamp(time), "1"]
          response['data']['result'].append(json_metric)
      
      elif query == "cell_ul_bitrate_bps":
          json_metric_ran['value'] = [datetime.timestamp(time), str(round(random.uniform(0,1),2))]
          response['data']['result'].append(json_metric_ran)
  
      elif query == "error":
          json_metric['value'] = [datetime.timestamp(time), "string"]
          response['data']['result'].append(json_metric)

    return response

@app.get("/osm/api/v1/query_range")
async def query_range(start: datetime, query: str, end: datetime = None, step: str = None, X_Gravitee_Api_Key: str = Header(None)):
    # /query_range?query=up&
    #              start=2015-07-01T20:10:30.781Z&
    #              end=2015-07-01T20:11:00.781Z&
    #              step=1m

    if X_Gravitee_Api_Key == None:
        return JSONResponse(status_code=404, content={"status": "Error", "message": "Header 'X-Gravitee-Api-Key' required."})
    if query == None:
        return JSONResponse(status_code=404, content={"status": "Error", "message": "Query required."})
    if start != None and end != None and start >= end:
        return JSONResponse(status_code=404, content={"status": "Error", "message": "Start is greater or equals than the end."})
    if end != None and step is None:
        return JSONResponse(status_code=404, content={"status": "Error", "message": "Interval datetime needs step."})
    if step != None:
        if step[:-1].isdigit() and step[-1] in ['s', 'm', 'h', 'M', 'y']:
            step_time = int(step[:-1])
            step_unit = step[-1]
        else:
            return JSONResponse(status_code=404, content={"status": "Error", "message": "Step is a integer followed by format ['s', 'm', 'h', 'M', 'y']."})
    else:
        step_time = None
        step_unit = None
    
    # Random response
    if generate_response() == '500':
      return JSONResponse(status_code=500, content={"status": "Error", "message": "Faild to connect to OSM."})

    dates = get_interval_datetimes(start, end, step_time, step_unit)

    response = {
        "status": "success",
        "data": {
            "resultType" : "matrix",
            "result" : []
        }
    }
    json_metric = {
        "metric": {
            "__name__" : query,
            "job" : "prometheus",
            "instance" : "http://5gzorro_osm.com"
        },
        "values": []
    }
    for date in dates:
        if query == "osm_requests":
            json_metric['values'].append([datetime.timestamp(date), str(round(random.uniform(0,1),2))])
        
        elif query == "availability":
            json_metric['values'].append([datetime.timestamp(date), str(round(generate_availability(), 2))])
            
        elif query == "up":
            json_metric['values'].append([datetime.timestamp(date), "1"])
    
        elif query == "error":
            json_metric['values'].append([datetime.timestamp(date), "string"])
            
    response['data']['result'].append(json_metric)

    return response