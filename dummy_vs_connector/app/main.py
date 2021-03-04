''' Dummy Vertical Slicer
Config with:
        Business Flow ID
        DL Kafka topic
        sliceID
        metricName:
                metricType
                aggregationMethod
                aggregationTimeline
        timestamp
'''

import requests, json, datetime
from uuid import uuid4
from random import randint
from fastapi import FastAPI

app = FastAPI()

def converter(o):
        if isinstance(o, datetime.datetime):
                return o.__str__()

@app.post("/sendConfig")
async def send_config_mda():
        config = {
                "businessID": str(uuid4()),
                "topic": "postData",
                "sliceID": randint(100,999),
                "metrics": [
                        {
                                "metricName": "cpu_utilization",
                                "metricType": "float",
                                "aggregationMethod": None,
                                "aggregationTimeline": None,
                                "aggregationInterval": None
                        },
                        {
                                "metricName": "ram_utilization",
                                "metricType": "float",
                                "aggregationMethod": None,
                                "aggregationTimeline": None,
                                "aggregationInterval": None
                        },
                        {
                                "metricName": "disk_usage",
                                "metricType": "float",
                                "aggregationMethod": None,
                                "aggregationTimeline": None,
                                "aggregationInterval": None
                        }
                ],
                "timestamp": json.dumps(datetime.datetime.now(), default=converter)
        }

        
        response = requests.post('http://mda:4000/set/', json=config).json()
        return "chega"

'''
if __name__ == "__main__":
        response = send_config_mda()
        print(response)
'''
