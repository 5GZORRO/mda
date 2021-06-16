import requests, json, datetime
from uuid import uuid4
from random import randint
from fastapi import FastAPI

app = FastAPI()

def converter(o):
	if isinstance(o, datetime.datetime):
		return o.__str__()


@app.get("/enableConfig")
async def send_config_mda():
	config = {
		"transactionID": randint(100,999),
		"topic": "postData",
		"networkID": randint(100,999),
		"metrics": [
				{
						"metricName": "cpu_utilization",
						"metricType": "float",
						"aggregationMethod": None,
						"timestampStep": "30s"
				},
				{
						"metricName": "ram_utilization",
						"metricType": "float",
						"aggregationMethod": None,
						"timestampStep": "1m"
				},
				{
						"metricName": "disk_usage",
						"metricType": "float",
						"aggregationMethod": None,
						"timestampStep": "2m"
				}
		],
		"timestampStart": "2021-03-12T11:34:00",
		"timestampEnd": "2021-03-26T18:34:00"
		#"timestamp_start": json.dumps(datetime.datetime.now(), default=converter),
		#"timestamp_final": json.dumps(datetime.datetime.now(), default=converter)
	}


	response = requests.post('http://mda:4000/settings', json=config).json()
	return response



@app.get("/enableConfig/<id>")
async def enable_config_mda(id):
	url = 'http://mda:4000/settings/'
	config_id = str(id)+'/enable'
	request_url = "{}/{}".format(url, config_id)
	response = requests.put(request_url)
	return response


@app.get("/disableConfig/<id>")
async def disable_config_mda(id):
	url = 'http://mda:4000/settings/'
	config_id = str(id)+'/disable'
	request_url = "{}/{}".format(url, config_id)
	response = requests.put(request_url)
	return response

@app.get("/updateConfig/<id>")
async def update_config_mda(id):
	url = 'http://mda:4000/settings/'
	config_id = str(id)
	request_url = "{}/{}".format(url, config_id)

	config = {
		"metrics": [
				{
						"metricName": "cpu_utilization",
						"metricType": "float",
						"aggregationMethod": None,
						"timestampStep": "35s"
				},
				{
						"metricName": "ram_utilization",
						"metricType": "float",
						"aggregationMethod": None,
						"timestampStep": "50s"
				},
				{
						"metricName": "disk_usage",
						"metricType": "float",
						"aggregationMethod": None,
						"timestampStep": "2m"
				}
		],
		"timestampStart": "2021-03-12T11:34:00",
		"timestampEnd": "2021-03-26T15:34:00"
	}


	response = requests.put(request_url, json=config).json()
	return response

@app.get("/deleteConfig/<id>")
async def delete_config_mda(id):
	url = 'http://mda:4000/settings/'
	config_id = str(id)
	request_url = "{}/{}".format(url, config_id)
	response = requests.delete(request_url)
	return response

@app.get("/getConfig/<id>")
async def get_id_config_mda(id):
	url = 'http://mda:4000/settings/'
	config_id = str(id)
	request_url = "{}/{}".format(url, config_id)
	response = requests.get(request_url)
	return response

@app.get("/getConfig")
async def get_config_mda():
	response = requests.get('http://mda:4000/settings')
	return response

