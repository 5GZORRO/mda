from fastapi import FastAPI
import uuid, random, requests, json, hashlib, os, rsa, sys, datetime, trace, threading, time
from Crypto.PublicKey import RSA
from pydantic import BaseModel
from typing import Optional, List
from kafka import KafkaProducer
from fastapi.responses import JSONResponse
from sqlalchemy import *
from sqlalchemy import create_engine
from sqlalchemy_utils import database_exists, create_database
from sqlalchemy.orm import scoped_session, sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
import sqlalchemy.dialects.postgresql as postgresql

POSTGRES_USER = os.environ["POSTGRES_USER"]
POSTGRES_PW = os.environ["POSTGRES_PW"]
POSTGRES_URL = os.environ["POSTGRES_URL"]
POSTGRES_DB = os.environ["POSTGRES_DB"]
publicKeyOperator = os.environ.get("OPERATOR_PUBLIC_KEY")

class Metric_Model(BaseModel):
	metricName: str
	metricType: str
	aggregationMethod: str = None
	timestampStep: str

class Config_Model(BaseModel):
	businessID: int
	topic: str
	networkID: int
	metrics: List[Metric_Model]
	timestampStart: Optional[str] = datetime.datetime.now()
	timestampEnd: Optional[str] = None

class Update_Config_Model(BaseModel):
	timestampStart: Optional[str] = None
	timestampEnd: Optional[str] = None
	metrics: Optional[List[Metric_Model]] = None

class Response_Config_Model(BaseModel):
	id: uuid.UUID
	created_at: datetime.datetime
	updated_at: datetime.datetime
	businessID: int
	topic: str
	networkID: int
	timestampStart: datetime.datetime
	timestampEnd: datetime.datetime
	metrics: List[Metric_Model]
	status: int

class Response_Error_Model(BaseModel):
	status: str
	message: str

from .database import *

class thread_with_trace(threading.Thread): 
	def __init__(self, *args, **keywords): 
		threading.Thread.__init__(self, *args, **keywords) 
		self.killed = False

	def start(self): 
		self.__run_backup = self.run 
		self.run = self.__run       
		threading.Thread.start(self) 

	def __run(self): 
		sys.settrace(self.globaltrace) 
		self.__run_backup() 
		self.run = self.__run_backup 

	def globaltrace(self, frame, event, arg): 
		if event == 'call': 
			return self.localtrace 
		else: 
			return None

	def localtrace(self, frame, event, arg): 
		if self.killed: 
			if event == 'line': 
				raise SystemExit() 
		return self.localtrace 

	def kill(self): 
		self.killed = True

app = FastAPI()

# Json response example
json_response_enable = {"id": "ab51f3e1-7b61-4f9d-85a4-9e9f366b593b","created_at": "2021-03-11T11:34:00.402075","updated_at": "null","businessID": 36574564,"topic": "postData","networkID": 232,"timestampStart": "2021-03-11T11:34:00","timestampEnd": "null","metrics": [{"metricName": "cpu_utilization","metricType": "float","aggregationMethod": "agg","timestampStep": "1h"}],"status": 1}
json_response_disable = json_response_enable.copy()
json_response_disable['status'] = 0


seconds_per_unit = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}
threads = {}

def convert_to_seconds(s):
	return int(s[:-1]) * seconds_per_unit[s[-1]]

def validate_uuid4(uuid_string):
	try:
		uuid.UUID(uuid_string).hex
	except ValueError:
		return False
	return True

def request_OSM(request_metric, request_start):
	endpoint = 'http://osm:4500/monitoringData?'
	request_url = endpoint + request_metric + request_start
	print(request_url)
	response = requests.get(request_url)
	#print('entra2')
	if response.status_code != 200:
		#print('entra')
		return ('Error in fetching data!', 200)
	#print(f'Response: {response}')
	resp = response.text
	json_data = json.loads(response.text)
	print(f'Response from OSM: {resp} + operator public key: {publicKeyOperator}')
	#json_data = {'counter':2}

	payload_encoded = {k: str(v).encode('utf-8') for k,v in json_data.items()}
	hashData = {k: hashlib.sha256(v).hexdigest() for k,v in payload_encoded.items()}
	print(f'Hashed Data: {hashData}')
	pKey = RSA.importKey(publicKeyOperator)
	print(f'Operator Public Key: {pKey}')

	dataHashEncrypt =  {rsa.encrypt(k.encode(), pKey): rsa.encrypt(v.encode(), pKey) for k,v in hashData.items()}
	print(f'Signup Data: {dataHashEncrypt}')

	# Data Lake Kafka Topic
	producer = KafkaProducer(bootstrap_servers=['kafka:9092'], api_version=(0,10,1))
	#producer = KafkaProducer(bootstrap_servers=['kafka:9092'], value_serializer=lambda x:json.dumps(x).encode('utf-8'), api_version=(0,10,1))
	print("Post Data into Kafka Topic")
	
	producer.send('topic_test', key=list(dataHashEncrypt.keys())[1], value=list(dataHashEncrypt.values())[1])
	return "Post Data into Data Lake sucessfull"


# curl 'http://localhost:9090/api/v1/query?query=cpu_utilization&time=2015-07-01T20:10:51.781Z'
def fetch_values(metric_id, metric_name, starttime , timeout, status, step):
	''' 2 situations that can happen
		1. VS sends with timestamp fields filled (not null):
			- verify start time
			- verify end time
			- verify status
		2. VS sends null timestamp fields:
			- timestamp start: datetime.datetime.now() - default
			- timestamp end: null (expects disable order)
			- verify status 
	'''
	request_metric = "match="+metric_name+"&"
	request_start = "start="+str(starttime)
	print(f'Start Fetching values of metric: {metric_id} - {metric_name}')
	if (timeout != None):
		while((datetime.datetime.now() >= starttime) and (datetime.datetime.now() < timeout) and status==1):
			print(f'{datetime.datetime.now()} - S1: Fetching values from OSM, metric: {metric_name}, step: {step}')
			request_OSM(request_metric, request_start)
			#print('teste aqui')
			#print(step)
			time.sleep(convert_to_seconds(step))
			#time.sleep(10)
	else:
		while(status == 1):
			#print('entraste')
			print(f'{datetime.datetime.now()} - S2: Fetching values from OSM, metric: {metric_name}, step: {step}')
			request_OSM(request_metric, request_start)
			time.sleep(convert_to_seconds(step))
	print('fim')
	return f'Done Fetching values of metric: {metric_id} - {metric_name}'

	'''while((datetime.datetime.now() < timeout) and int(status)==1):
					print(f'{datetime.datetime.now()} - Fetching values from OSM, metric: {metric["metricName"]}, step: {metric["timestampStep"]}')
			
					request_metric = "query="+metric["metricName"]+"&"
					request_start = "time="+str(datetime.datetime.now())
			
					request_OSM(request_metric, request_start)
					time.sleep(convert_to_seconds(metric["timestampStep"]))
				return f'Done Fetching values of metric: {metric["id"]} - {metric["metricName"]}'''

def transform_config(metric_id, metric_name, timestampStart, timestampEnd, status, step):
	global threads
	obj = thread_with_trace(target = fetch_values, args=(metric_id, metric_name, timestampStart, timestampEnd, status, step))
	threads[str(metric_id)] = obj
	threads[str(metric_id)].start()
	print(f'{datetime.datetime.now()} - Active Threads {threading.active_count()}')

def delete_thread(metric_id):
	global threads
	print('entra3')
	print(metric_id)
	print(threads)
	print(threads[str(metric_id)])
	# stop thread and remove from global dict the assign
	threads[str(metric_id)].kill()
	threads[str(metric_id)].join()
	print(f'Stop Fetching values of metric: {metric_id}')
	if metric_id in threads.keys():
		del threads[metric_id]
	return



'''def run_thread(config: Config_Model):
	# Request get metric values from OSM
	request_metrics = ''
	for i in range(len(config.metrics)):
		metric = "match="+config.metrics[i]['metricName']+"&"
		request_metrics += metric
	request_metrics = request_metrics + "start=" + config.timestamp.replace('"','')
	if config.timestamp_final != None:
		request_metrics = request_metrics + "&end=" + config.timestamp_final
	if config.step != None:
		request_metrics = request_metrics + "&step=" + config.step
	endpoint = 'http://osm:4500/monitoringData?'
	request_url = endpoint + request_metrics
	response = requests.get(request_url)
	if response.status_code != 200:
		return ('Error in fetching data!', 200)
	resp = response.text
	payload_encoded = {k: str(v).encode('utf-8') for k,v in resp.items()}
	hashData = {k: hashlib.sha256(v).hexdigest() for k,v in payload_encoded.items()}
	pKey = RSA.importKey(publicKeyOperator)
	dataHashEncrypt =  {k: rsa.encrypt(v.encode(), pKey) for k,v in hashData.items()}
	# Data Lake Kafka Topic
	producer = KafkaProducer(bootstrap_servers=['kafka:9092'], value_serializer=lambda x:json.dumps(x).encode('utf-8'), api_version=(0,10,1))
	print("send to DL Topic")
	data = {'counter':2}
	producer.send('topic_test', value=dataHashEncrypt)
	return "Pipeline completed"'''

# ----------------------------------------------------------------#
@app.on_event("shutdown")
def shutdown_event():
	print('exit')
	global threads
	for i in threads.keys():
		del threads[i]

# ----------------------------------------------------------------#

@app.post("/settings", status_code=201, responses={201: {"model": Response_Config_Model,
														 "content": {"application/json": {
																	 "example": json_response_enable}}},
												   404: {"model": Response_Error_Model,
														 "content": {"application/json": {
																	 "example": {"status": "Error", "message": "Error message."}}}}})
async def set_param(config: Config_Model):
	# Save config in database
	resp = add_config(config)
	if resp == -1:
	  return JSONResponse(status_code=404, content={"status": "Error", "message": "Error in create config in database."})

	# Run threads
	for metric in resp['metrics']:
	  transform_config(metric['id'], metric['metricName'], resp['timestampStart'], resp['timestampEnd'], resp['status'], metric['timestampStep'])
	  del metric['id']

	return resp

@app.get("/settings/{config_id}", responses={200: {"model": Response_Config_Model,
												   "content": {"application/json": {
															   "example": json_response_enable}}},
											 404: {"model": Response_Error_Model,
												   "content": {"application/json": {
															   "example": {"status": "Error", "message": "Error message."}}}}})
async def get_config_id(config_id):
	# Get config by id
	if validate_uuid4(config_id) is False:
	  return JSONResponse(status_code=404, content={"status": "Error", "message": "Config id invalid."})
	resp = get_config(config_id)
	if resp == 0:
	  return JSONResponse(status_code=404, content={"status": "Error", "message": "Config id invalid."})
	if resp == -1:
	  return JSONResponse(status_code=404, content={"status": "Error", "message": "Error in get config in database."})

	for metric in resp['metrics']:
		  del metric['id']

	return resp

@app.get("/settings", responses={200: {"model": List[Response_Config_Model],
									   "content": {"application/json": {
												   "example": [json_response_enable]}}},
								 404: {"model": Response_Error_Model,
									   "content": {"application/json": {
												   "example": {"status": "Error", "message": "Error message."}}}}})
async def get_all_configs():
	# Get configs
	#print('teste1')
	resp = get_configs()
	#print('teste2')
	if resp == -1:
	  return JSONResponse(status_code=404, content={"status": "Error", "message": "Error in get config in database."})
	return resp

@app.put("/settings/{config_id}", responses={200: {"model": Response_Config_Model,
												   "content": {"application/json": {
															   "example": json_response_enable}}},
											 404: {"model": Response_Error_Model,
												   "content": {"application/json": {
															   "example": {"status": "Error", "message": "Error message."}}}}})
async def update_config_id(config_id, config: Update_Config_Model):
	# Update config by id
	if validate_uuid4(config_id) is False:
	  return JSONResponse(status_code=404, content={"status": "Error", "message": "Config id invalid."})
	resp1 = get_config(config_id)
	resp2 = update_config(config_id, config)
	if resp1 == 0 or resp2 == 0:
	  return JSONResponse(status_code=404, content={"status": "Error", "message": "Config id invalid."})
	if resp1 == 1:
	  return JSONResponse(status_code=404, content={"status": "Error", "message": "No body data to update."})
	if resp1 == -1 or resp2 == -1:
	  return JSONResponse(status_code=404, content={"status": "Error", "message": "Error in update config in database."})

	# Delete old threads
	for metric in resp1['metrics']:
	  delete_thread(metric['id'])
	  del metric['id']

	# Run threads
	for metric in resp2['metrics']:
	  transform_config(metric['id'], metric['metricName'], resp['timestampStart'], resp['timestampEnd'], resp['status'], metric['timestampStep'])
	  del metric['id']

	return resp2

@app.put("/settings/{config_id}/enable", responses={200: {"model": Response_Config_Model,
														  "content": {"application/json": {
																	  "example": json_response_enable}}},
													404: {"model": Response_Error_Model,
														  "content": {"application/json": {
																	  "example": {"status": "Error", "message": "Error message."}}}}})
async def enable_config_id(config_id):
	# Enable config by id
	if validate_uuid4(config_id) is False:
	  return JSONResponse(status_code=404, content={"status": "Error", "message": "Config id invalid."})
	resp = enable_config(config_id)
	if resp == 0:
	  return JSONResponse(status_code=404, content={"status": "Error", "message": "Config id invalid."})
	if resp == 1:
	  return JSONResponse(status_code=404, content={"status": "Error", "message": "Config already enabled."})
	if resp == -1:
	  return JSONResponse(status_code=404, content={"status": "Error", "message": "Error in enable config in database."})

	# Run threads
	for metric in resp['metrics']:
	  transform_config(metric['id'], metric['metricName'], resp['timestampStart'], resp['timestampEnd'], resp['status'], metric['timestampStep'])
	  del metric['id']

	return resp

@app.put("/settings/{config_id}/disable", responses={200: {"model": Response_Config_Model,
														   "content": {"application/json": {
																	   "example": json_response_disable}}},
													 404: {"model": Response_Error_Model,
														   "content": {"application/json": {
																	   "example": {"status": "Error", "message": "Error message."}}}}})
async def disable_config_id(config_id):
	# Disable config by id
	if validate_uuid4(config_id) is False:
	  return JSONResponse(status_code=404, content={"status": "Error", "message": "Config id invalid."})
	resp = disable_config(config_id)
	if resp == 0:
	  return JSONResponse(status_code=404, content={"status": "Error", "message": "Config id invalid."})
	if resp == 1:
	  return JSONResponse(status_code=404, content={"status": "Error", "message": "Config already disabled."})
	if resp == -1:
	  return JSONResponse(status_code=404, content={"status": "Error", "message": "Error in disable config in database."})

	# Delete old threads
	for metric in resp['metrics']:
	  delete_thread(metric['id'])
	  del metric['id']

	return resp

@app.delete("/settings/{config_id}", status_code=204,
									 responses={404: {"model": Response_Error_Model,
													  "content": {"application/json": {
																  "example": {"status": "Error", "message": "Error message."}}}}})
async def delete_config_id(config_id):
	# Get config by id
	if validate_uuid4(config_id) is False:
	  return JSONResponse(status_code=404, content={"status": "Error", "message": "Config id invalid."})
	resp1 = get_config(config_id)
	resp2 = delete_config(config_id)
	if resp1 == 0 or resp2 == 0:
	  return JSONResponse(status_code=404, content={"status": "Error", "message": "Config id invalid."})
	if resp1 == -1 or resp2 == -1:
	  return JSONResponse(status_code=404, content={"status": "Error", "message": "Error in delete config in database."})

	# Delete old threads
	for metric in resp1['metrics']:
	  delete_thread(metric['id'])
	  del metric['id']

	return JSONResponse(status_code=204, content=None)
