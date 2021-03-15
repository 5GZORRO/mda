from typing import List
from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse
from datetime import datetime
from dateutil.relativedelta import relativedelta
import random, requests

import urllib.parse as urlparse
from urllib.parse import parse_qs

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

# ----------------------------------------------------------------#

@app.get("/monitoringData")
async def monitoring_data(start: datetime, match: List[str] = Query([], min_length=1), end: datetime = None, step: str = None):
    # /monitoringData?match[]=up&match[]=up&
    #            start=2015-07-01T20:10:30.781Z&
    #            end=2015-07-01T20:11:00.781Z&
    #            step=1m

    if len(match) < 1:
        return JSONResponse(status_code=404, content={"status": "Error", "message": "Match required."})
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
    for metric in match:
        json_metric = {
            "metric": {
                "__name__" : metric,
                "job" : "prometheus",
                "instance" : "http://5gzorro_osm.com"
            },
            "values": []
        }
        for date in dates:
            json_metric['values'].append([datetime.timestamp(date), round(random.uniform(0,1),2)])
        response['data']['result'].append(json_metric)

    return response