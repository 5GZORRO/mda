from fastapi import FastAPI, Response
from starlette.status import HTTP_204_NO_CONTENT
import uuid, random, requests, json, hashlib, os, rsa, sys, datetime, trace, time, logging
from threading import Thread
from queue import PriorityQueue
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
import psycopg2
import psycopg2.extras
from dateutil.relativedelta import relativedelta
from timeloop import Timeloop
from datetime import timedelta
logging.basicConfig(filename='logs/'+'mda.json', level=logging.CRITICAL, format='{ "timestamp": "%(asctime)s.%(msecs)03dZ", %(message)s}', datefmt='%Y-%m-%dT%H:%M:%S')

# Environment variables 
try:
  POSTGRES_USER = os.environ["POSTGRES_USER"]
  POSTGRES_PW = os.environ["POSTGRES_PW"]
  POSTGRES_URL = os.environ["POSTGRES_URL"]
  POSTGRES_DB = os.environ["POSTGRES_DB"]
  RESET_DB = os.environ["RESET_DB"]
  
  KAFKA_HOST = os.environ["KAFKA_HOST"]
  KAFKA_PORT = os.environ["KAFKA_PORT"]
  
  #publicKeyOperator = os.environ["OPERATOR_PUBLIC_KEY"]
except Exception as e:
  print("Environment variable does not exists.")
  sys.exit(0)

class Metric_Model(BaseModel):
  metricName: str
  metricType: str
  aggregationMethod: str = None
  step: str
  next_run_at: Optional[str] = None

class Config_Model(BaseModel):
  businessID: str
  topic: str
  networkID: int
  tenantID: str
  resourceID: str
  referenceID: str
  metrics: List[Metric_Model]
  timestampStart: Optional[datetime.datetime] = datetime.datetime.now()
  timestampEnd: Optional[datetime.datetime] = None

class Update_Config_Model(BaseModel):
  timestampEnd: Optional[datetime.datetime] = None
  metrics: Optional[List[Metric_Model]] = None

class Response_Config_Model(BaseModel):
	id: uuid.UUID
	created_at: datetime.datetime
	updated_at: datetime.datetime
	businessID: str
	topic: str
	networkID: int
	timestampStart: datetime.datetime
	timestampEnd: datetime.datetime
	metrics: List[Metric_Model]
	status: int
	tenantID: str
	resourceID: str
	referenceID: str

class Response_Error_Model(BaseModel):
	status: str
	message: str

# Json response example
json_response_enable = {"id": "ab51f3e1-7b61-4f9d-85a4-9e9f366b593b","created_at": "2021-03-11T11:34:00.402075","updated_at": "null","businessID": 36574564,"businessID": "business1", "topic": "test1", "networkID": 1, "tenantID": "tenant1", "referenceID": "reference1", "resourceID": "resource1","timestampStart": "2021-03-11T11:34:00","timestampEnd": "null","metrics": [{"metricName": "cpu_utilization","metricType": "float","aggregationMethod": "agg","step": "1h"}],"status": 1}
json_response_disable = json_response_enable.copy()
json_response_disable['status'] = 0


wait_queue = PriorityQueue()
metrics_queue = PriorityQueue()
num_fetch_threads = 10
first_metric_aux = None
update_queue_flag = False

from .database import *

def info_log(status, message):
	logging.critical('"status": "'+str(status)+'", "message": "'+message+'"')

# Update first metric to read
def update_first_metric_aux():
  global wait_queue
  if wait_queue.empty():
    return None
  aux = wait_queue.get()
  wait_queue.put(aux)
  return aux[0]
  
def request_orchestrator(request_metric, request_schedule, resourceID, referenceID, next_run_at, tenantID, businessID, networkID, kafka_topic):
  try:
    # curl TBD to 'http://localhost:9090/api/v1/query=cpu_utilization&time=2015-07-01T20:10:51'
    endpoint = 'http://osm:4500/monitoringData?'
    request_url = endpoint + request_metric + request_schedule
    response = requests.get(request_url)
    if response.status_code != 200:
      info_log(400, "Request to OSM not sucessful")
      #print(f'Error: Request to OSM not successful')
      return('Error in fetching data!', 200)
    resp = response.text
    json_data = json.loads(resp)
    info_log(None, f'Response from OSM: {resp}')
  
    # Create JSON object that will be sent to DL Kafka Topic
    monitoringData = {
        "metricName" : json_data["data"]["result"][0]["metric"]["__name__"],
        "metricValue" : json_data["data"]["result"][0]["values"][0][1],
        "resourceID" : resourceID,
        "referenceID" : referenceID,
        "timestamp" : str(next_run_at)
    }
    
    dataHash = {
        "data" : monitoringData
    }
  
    data = {
        "operatorID" : tenantID,
        "businessID" : businessID,
        "networkID" : networkID
    }
    data["monitoringData"] = monitoringData
  
    payload_encoded = {k: str(v).encode('utf-8') for k, v in dataHash.items()}
    hashData = {k: hashlib.sha256(v).hexdigest() for k,v in payload_encoded.items()}
    info_log(None, f'Raw Data: {data} \nHashed Data: {hashData}')
  
    public_key, private_key = rsa.newkeys(1024)
  
    dataHashEncrypt = {rsa.encrypt(k.encode(), private_key): rsa.encrypt(v.encode(), private_key) for k,v in hashData.items()}
    info_log(None, f'Signup Data: {dataHashEncrypt}')
  
    producer = KafkaProducer(bootstrap_servers=[KAFKA_HOST+':'+KAFKA_PORT], value_serializer=lambda x: json.dumps(x).encode('utf-8'), api_version=(0,10,1))
    producer.send('topic_test', key=list(dataHashEncrypt.values())[0],  value=data)
    info_log(200, f'Post Data into DL Kafka Topic {kafka_topic}')
    return 1
  except Exception as e:
    info_log(400, 'Erro in request_orchestrator: ' + str(e))
    return 0

# Worker thread function
def queue_consumer(i, q):
  global update_queue_flag
  while True:
    next_item = q.get()
    request_metric = "match="+next_item[5]+"&"
    request_schedule = "start="+str(next_item[0]) 
    info_log(None, f'Start Fetching Values of Metric: {next_item[5]} (Thread Associated: {i})')
    info_log(None, f'{datetime.datetime.now()} - UC1: Fetching values from OSM, metric: {next_item[5]} (Step Associated: {next_item[2]})')
    request_orchestrator(request_metric, request_schedule, next_item[12], next_item[13], next_item[0], next_item[11], next_item[8], next_item[10], next_item[9])
    
    # after completed the sign/push operations we must perform a query to the db modifying the next_run_at
    update_next_run(next_item[4], next_item[3])
    update_queue_flag = True
    q.task_done()
   
def validate_uuid4(uuid_string):
  try:
    uuid.UUID(uuid_string).hex
  except ValueError:
  	return False
  return True
# --------------------- START SCRIPT -----------------------------#
# ----------------------------------------------------------------#
# Load database metrics to wait queue
load_database_metrics()

# Update first metric to read
first_metric_aux = update_first_metric_aux()

# Set up threads to fetch the metrics
for i in range(num_fetch_threads):
	worker = Thread(target=queue_consumer, args=(i, metrics_queue,))
	worker.setDaemon(True)
	worker.start()

# Check waiting metrics
tl = Timeloop()
@tl.job(interval=timedelta(seconds=1))
def check_waiting_metrics():
  global metrics_queue
  global wait_queue
  global update_queue_flag
  global first_metric_aux
  '''print('RUN TIMELOOP')
  print('metrics_queue')
  print(metrics_queue.queue)
  print('wait_queue')
  print(wait_queue.queue)
  print('update_queue_flag')
  print(update_queue_flag)
  print('first_metric_aux')
  print(first_metric_aux)
  print('now')
  print(str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))'''
  if update_queue_flag:
    first_metric_aux = update_first_metric_aux()
    update_queue_flag = False
  if first_metric_aux != None and str(first_metric_aux) <= str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")):
    metrics_queue.put(wait_queue.get())
    first_metric_aux = update_first_metric_aux()
  return
tl.start(block=False)

# ----------------------- MAIN APP -------------------------------#
# ----------------------------------------------------------------#

app = FastAPI()

@app.on_event("shutdown")
def shutdown_event():
  print('exit')
  global metrics_queue
  global wait_queue
  wait_queue.join()
  metrics_queue.join()
  return

# ----------------- REST FASTAPI METHODS -------------------------#
# ----------------------------------------------------------------#

@app.post("/settings", status_code=201, responses={201: {"model": Response_Config_Model,
														 "content": {"application/json": {
																	 "example": json_response_enable}}},
												   404: {"model": Response_Error_Model,
														 "content": {"application/json": {
																	 "example": {"status": "Error", "message": "Error message."}}}}})
async def set_param(config: Config_Model):
  global update_queue_flag
  if config.timestampStart < datetime.datetime.now():
    return JSONResponse(status_code=404, content={"status": "Error", "message": "Timestamp start need to be after current now."})
  if config.timestampEnd != None and config.timestampStart > config.timestampEnd:
    return JSONResponse(status_code=404, content={"status": "Error", "message": "Timestamp start need to be after timestamp end."})
  # Save config in database
  resp = add_config(config)
  if resp == -1:
    return JSONResponse(status_code=404, content={"status": "Error", "message": "Error in create config in database."})
  update_queue_flag = True
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
  return resp

@app.get("/settings", responses={200: {"model": List[Response_Config_Model],
									   "content": {"application/json": {
												   "example": [json_response_enable]}}},
								 404: {"model": Response_Error_Model,
									   "content": {"application/json": {
												   "example": {"status": "Error", "message": "Error message."}}}}})
async def get_all_configs():
  # Get configs
  resp = get_configs()
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
  global update_queue_flag
  # Update config by id
  if validate_uuid4(config_id) is False:
    return JSONResponse(status_code=404, content={"status": "Error", "message": "Config id invalid."})
  resp = update_config(config_id, config)
  if resp == 0:
    return JSONResponse(status_code=404, content={"status": "Error", "message": "Config id invalid."})
  if resp == 1:
    return JSONResponse(status_code=404, content={"status": "Error", "message": "Arguments invalid."})
  if resp == 2:
    return JSONResponse(status_code=404, content={"status": "Error", "message": "Timestamp end must be superior to the actual."})
  if resp == -1:
    return JSONResponse(status_code=404, content={"status": "Error", "message": "Error in update config in database."})
    update_queue_flag = True
  return resp

@app.put("/settings/{config_id}/enable", responses={200: {"model": Response_Config_Model,
														  "content": {"application/json": {
																	  "example": json_response_enable}}},
													404: {"model": Response_Error_Model,
														  "content": {"application/json": {
																	  "example": {"status": "Error", "message": "Error message."}}}}})
async def enable_config_id(config_id):
  global update_queue_flag
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
  update_queue_flag = True
  return resp

@app.put("/settings/{config_id}/disable", responses={200: {"model": Response_Config_Model,
														                               "content": {"application/json": {
                                                           "example": json_response_disable}}},
													 404: {"model": Response_Error_Model,
														   "content": {"application/json": {
																	   "example": {"status": "Error", "message": "Error message."}}}}})
async def disable_config_id(config_id):
  global update_queue_flag
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
  update_queue_flag = True
  return resp

@app.delete("/settings/{config_id}", status_code=HTTP_204_NO_CONTENT, responses={404: {"model": Response_Error_Model,
													  "content": {"application/json": {
																  "example": {"status": "Error", "message": "Error message."}}}}})
async def delete_config_id(config_id):
  global update_queue_flag
  # Get config by id
  if validate_uuid4(config_id) is False:
    return JSONResponse(status_code=404, content={"status": "Error", "message": "Config id invalid."})
  resp = delete_config(config_id)
  if resp == 0:
    return JSONResponse(status_code=404, content={"status": "Error", "message": "Config id invalid."})
  if resp == -1:
    return JSONResponse(status_code=404, content={"status": "Error", "message": "Error in delete config in database."})
  update_queue_flag = True
  return Response(status_code=HTTP_204_NO_CONTENT)
