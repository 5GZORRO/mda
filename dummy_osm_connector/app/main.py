from typing import List
from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta
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
            curr_date = curr_date + timedelta(seconds=step_time)
        elif step_unit  == 'm':
            curr_date = curr_date + timedelta(minutes=step_time)
        elif step_unit  == 'h':
            curr_date = curr_date + timedelta(hours=step_time)
    return datetimes


@app.get("/dummyData")
async def dummy_data(start: datetime, match: List[str] = Query([], min_length=1), end: datetime = None, step: str = None):
    # /dummyData?match[]=up&match[]=up&
    #            start=2015-07-01T20:10:30.781Z&
    #            end=2015-07-01T20:11:00.781Z&
    #            step=15s

    if len(match) < 1:
        return JSONResponse(
            status_code=400,
            content={"message": "match required"},
        )
    if start != None and end != None and start >= end:
        return JSONResponse(
            status_code=400,
            content={"message": "start is greater or equals than the end"},
        )

    if end != None and step is None:
        return JSONResponse(
            status_code=400,
            content={"message": "interval datetime needs step"},
        )

    if step != None:
        if step[:-1].isdigit() and step[-1] in ['s', 'm', 'h']:
            step_time = int(step[:-1])
            step_unit = step[-1]
        else:
            return JSONResponse(
                status_code=400,
                content={"message": "step is a integer followed by format ['s', 'm', 'h']"},
            )
    else:
        step_time = None
        step_unit = None

    dates = get_interval_datetimes(start, end, step_time, step_unit)

    response = {
        "status" : "success",
        "data" : {
            "resultType" : "matrix",
            "result" : []
        }
    }

    for metric in match:
        json_metric = {
            "metric" : {
                "__name__" : metric,
                "job" : "prometheus",
                "instance" : "http://5gzorro_osm.com"
            },
            "values" : []
        }

        for date in dates:
            json_metric['values'].append([datetime.timestamp(date), round(random.uniform(0,1),2)])

        response['data']['result'].append(json_metric)

    return response