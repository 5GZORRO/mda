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
logging.basicConfig(filename='logs/'+'mda.json', level=logging.INFO, format='{ "timestamp": "%(asctime)s.%(msecs)03dZ", %(message)s}', datefmt='%Y-%m-%dT%H:%M:%S')
logging.getLogger("uvicorn.error").setLevel(logging.CRITICAL)
logging.getLogger("kafka").setLevel(logging.CRITICAL)

# Environment variables 
try:
  POSTGRES_USER = os.environ["POSTGRES_USER"]
  POSTGRES_PW = os.environ["POSTGRES_PW"]
  POSTGRES_HOST = os.environ["POSTGRES_HOST"]
  POSTGRES_PORT = os.environ["POSTGRES_PORT"]
  POSTGRES_DB = os.environ["POSTGRES_DB"]
  RESET_DB = os.environ["RESET_DB"]
  
  KAFKA_HOST = os.environ["KAFKA_HOST"]
  KAFKA_PORT = os.environ["KAFKA_PORT"]
  
  NUM_READING_THREADS = int(os.environ["NUM_READING_THREADS"])
  NUM_AGGREGATION_THREADS = int(os.environ["NUM_AGGREGATION_THREADS"])
  
  #publicKeyOperator = os.environ["OPERATOR_PUBLIC_KEY"]
except Exception as e:
  print("Environment variable does not exists: " + str(e))
  sys.exit(0)

class Metric_Model(BaseModel):
  metric_name: str
  metric_type: str
  step: str
  aggregation_method: Optional[str] = None
  step_aggregation: Optional[str] = None

class Context_Model(BaseModel):
  resource_id: str
  network_slice_id: Optional[str] = None
  parent_id: Optional[str] = None

class Response_Metric_Model(BaseModel):
  metric_name: str
  metric_type: str
  step: str
  aggregation_method: Optional[str] = None
  step_aggregation: Optional[str] = None
  next_run_at: datetime.datetime
  next_aggregation: Optional[datetime.datetime] = None

class Config_Model(BaseModel):
  business_id: str
  topic: str
  monitoring_endpoint: str
  tenant_id: str
  reference_id: str
  context_ids: List[Context_Model]
  metrics: List[Metric_Model]
  timestamp_start: Optional[datetime.datetime] = None
  timestamp_end: Optional[datetime.datetime] = None

class Update_Config_Model(BaseModel):
  timestamp_end: Optional[datetime.datetime] = None
  metrics: Optional[List[Metric_Model]] = None

class Response_Config_Model(BaseModel):
  id: uuid.UUID
  created_at: datetime.datetime
  updated_at: datetime.datetime
  business_id: str
  monitoring_endpoint: str
  topic: str
  resource_id: str
  network_id: str
  parent_id: str
  timestamp_start: datetime.datetime
  timestamp_end: Optional[datetime.datetime] = None	
  metrics: List[Response_Metric_Model]
  status: int
  tenant_id: str
  reference_id: str

class Response_Error_Model(BaseModel):
	status: str
	message: str

# Json response example
json_response_enable = {"id": "ab51f3e1-7b61-4f9d-85a4-9e9f366b593b","created_at": "2021-03-11T11:34:00.402075","updated_at": "null","businessID": 36574564,"businessID": "business1", "topic": "test1", "networkID": 1, "tenantID": "tenant1", "referenceID": "reference1", "resourceID": "resource1","timestampStart": "2021-03-11T11:35:00","timestampEnd": "null","metrics": [{"metricName": "cpu_utilization","metricType": "float","aggregationMethod": "sum","step": "15min","step_aggregation": "1h", "next_run_at": "2021-03-11T11:45:00", "next_aggregation": "2021-03-11T12:35:00"}],"status": 1}
json_response_disable = json_response_enable.copy()
json_response_disable['status'] = 0

agg_options = ['SUM', 'AVG', 'MIN', 'MAX', 'COUNT', 'STDDEV']

step_options = ['s', 'm', 'h', 'd', 'w']

# Metrics
wait_queue = PriorityQueue()
metrics_queue = PriorityQueue()
num_fetch_threads = NUM_READING_THREADS
first_metric_aux = None
update_queue_flag = False

#Aggregations
wait_queue_agg = PriorityQueue()
aggregation_queue = PriorityQueue()
num_fetch_threads_agg = NUM_AGGREGATION_THREADS
first_aggregation_aux = None
update_queue_flag_agg = False

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
  
# Update first aggregation to read
def update_first_aggregation_aux():
  global wait_queue_agg
  if wait_queue_agg.empty():
    return None
  aux = wait_queue_agg.get()
  wait_queue_agg.put(aux)
  return aux[0]
  
def send_kafka(data, dataHash, kafka_topic):
  try:
    payload_encoded = {k: str(v).encode('utf-8') for k, v in dataHash.items()}
    hashData = {k: hashlib.sha256(v).hexdigest() for k,v in payload_encoded.items()}
    #info_log(None, f'Raw Data: {data} \nHashed Data: {hashData}')
  
    public_key, private_key = rsa.newkeys(1024)
  
    dataHashEncrypt = {rsa.encrypt(k.encode(), private_key): rsa.encrypt(v.encode(), private_key) for k,v in hashData.items()}
    #info_log(None, f'Signup Data: {dataHashEncrypt}')
  
    producer = KafkaProducer(bootstrap_servers=[KAFKA_HOST+':'+KAFKA_PORT], value_serializer=lambda x: json.dumps(x).encode('utf-8'), api_version=(0,10,1))
    producer.send(kafka_topic, key=list(dataHashEncrypt.values())[0],  value=data)
    info_log(200, f'Post metric {data["monitoringData"]["metricName"]}, from operator {data["operatorID"]}, into DL Kafka Topic {kafka_topic} [Post Time: {data["monitoringData"]["timestamp"]}]')
    return 1
  except Exception as e:
    info_log(400, 'Erro in request_orchestrator: ' + str(e))
    return 0
  
def send_aggregation(metric_name, resourceID, referenceID, next_run_at, tenantID, businessID, networkID, kafka_topic, aggregation, metric_id, next_aggregation, step_aggregation):
  try:
    value = get_last_aggregation(metric_id, aggregation, next_aggregation, step_aggregation)
    # Create JSON object that will be sent to DL Kafka Topic
    monitoringData = {
      "metricName" : metric_name,
      "metricValue" : value,
      "resourceID" : resourceID,
      "referenceID" : referenceID,
      "timestamp" : str(next_run_at),
      "aggregationMethod": aggregation
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
    send_kafka(data, dataHash, kafka_topic)
    print('SEND AGGREGATION-> '+str(next_run_at)+' -> '+ str(value))
    return 1
  except Exception as e:
    print('send_aggregation-> ' + str(e))
    info_log(400, 'Erro in request_orchestrator: ' + str(e))
    return 0
  
def request_orchestrator(metric_name, resourceID, referenceID, next_run_at, tenantID, businessID, networkID, kafka_topic, aggregation, metric_id):
  try:
    request_metric = "match="+metric_name+"&"
    request_schedule = "start="+str(next_run_at) 
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
    
    if aggregation != None:
      #Save value in db
      insert_metric_value(metric_id, json_data["data"]["result"][0]["values"][0][1], next_run_at)
    else:
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
      send_kafka(data, dataHash, kafka_topic)
      print('SEND DATA-> '+str(next_run_at)+' -> '+ str(json_data["data"]["result"][0]["values"][0][1]))
    return 1
  except Exception as e:
    print('request_orchestrator-> ' + str(e))
    info_log(400, 'Erro in request_orchestrator: ' + str(e))
    return 0

# Worker thread function
def queue_consumer(i, q, f):
  global update_queue_flag
  global update_queue_flag_agg
  try:
    while True:
      next_item = q.get()
      
      if next_item[3] == None or next_item[0] <= next_item[3]:
        info_log(None, f'Start Fetching Values of Metric: {next_item[5]} (Thread Associated: {i})')
        if f == 1:
          #Send aggregation
          info_log(None, f'{datetime.datetime.now()} - UC1: Aggregating values from metric: {next_item[5]} (Step Aggregation Associated: {next_item[14]})')
          send_aggregation(next_item[5], next_item[12], next_item[13], next_item[0], next_item[11], next_item[8], next_item[10], next_item[9], next_item[7], next_item[4], next_item[15], next_item[14])
          update_aggregation(next_item[4], next_item[0])
        else:
          #Send metric
          request_orchestrator(next_item[5], next_item[12], next_item[13], next_item[0], next_item[11], next_item[8], next_item[10], next_item[9], next_item[7], next_item[4])
          info_log(None, f'{datetime.datetime.now()} - UC2: Fetching values from OSM, metric: {next_item[5]} (Step Associated: {next_item[2]}')
          update_next_run(next_item[4], next_item[0])
        
      q.task_done()
  except Exception as e:
    print(e)
   
def validate_uuid4(uuid_string):
  try:
    uuid.UUID(uuid_string).hex
  except ValueError:
  	return False
  return True

def delete_old_metric(metric_id, queue):
  global metrics_queue
  global aggregation_queue
  #print('DELETE INIT')
  index = True
  while(index):
    index = False
    if queue == 0:
      for i in range(len(metrics_queue.queue)):
        if metrics_queue.queue[i][4] == metric_id:
          #print('DELETE METRIC -> ' + str(datetime.datetime.now()) + ' -> ' + str(metric_id))
          del metrics_queue.queue[i]
          index = True
          break
    else:
      for i in range(len(aggregation_queue.queue)):
        if aggregation_queue.queue[i][4] == metric_id:
          #print('DELETE AGG -> ' + str(datetime.datetime.now()) + ' -> ' + str(metric_id))
          del aggregation_queue.queue[i]
          index = True
          break
  return
# --------------------- START SCRIPT -----------------------------#
# ----------------------------------------------------------------#
# Load database metrics to wait queue
load_database_metrics()

# Update first metric/aggregation to read
first_metric_aux = update_first_metric_aux()
first_aggregation_aux = update_first_aggregation_aux()

# Set up threads
for i in range(num_fetch_threads):
	worker = Thread(target=queue_consumer, args=(i, metrics_queue, 0,))
	worker.setDaemon(True)
	worker.start()
 
for i in range(num_fetch_threads_agg):
	worker = Thread(target=queue_consumer, args=(i, aggregation_queue, 1,))
	worker.setDaemon(True)
	worker.start()

# Check waiting metrics
tl = Timeloop()
logging.getLogger("timeloop").setLevel(logging.CRITICAL)
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
  try:
    if update_queue_flag:
      first_metric_aux = update_first_metric_aux()
      update_queue_flag = False
    if first_metric_aux != None and str(first_metric_aux) <= str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")):
      # Add to execution queue
      metric = list(wait_queue.get())
      #print('ADD METRIC -> ' + str(metric[5]) + ' -> ' + str(metric[0]))
      metrics_queue.put(tuple(metric))
      # Delete old metric
      sec_to_add = convert_to_seconds(metric[2])
      metric[0] = metric[0] - relativedelta(seconds=sec_to_add)
      #print('METRIC -> ' + str(metric[5]) + ' -> ' + str(metric[0]))
      while tuple(metric) in metrics_queue.queue:
        #print('DELETE METRIC -> ' + str(metric[5]) + ' -> ' + str(metric[0]))
        del metrics_queue.queue[metrics_queue.queue.index(tuple(metric))]
      # Add next to wait queue
      metric[0] = metric[0] + relativedelta(seconds=sec_to_add*2)
      #print('WAIT METRIC -> ' + str(metric[5]) + ' -> ' + str(metric[0]))
      wait_queue.put(tuple(metric))
      
      first_metric_aux = update_first_metric_aux()
    return
  except Exception as e:
    print('Timeloop metric -> ' + str(e))
    return -1
tl.start(block=False)

# Check waiting metrics
t2 = Timeloop()
logging.getLogger("timeloop").setLevel(logging.CRITICAL)
@t2.job(interval=timedelta(seconds=1))
def check_waiting_aggregations():
  global aggregation_queue
  global wait_queue_agg
  global update_queue_flag_agg
  global first_aggregation_aux
  '''print('RUN TIMELOOP')
  print('aggregation_queue')
  print(aggregation_queue.queue)
  print('wait_queue_agg')
  print(wait_queue_agg.queue)
  print('update_queue_flag_agg')
  print(update_queue_flag_agg)
  print('first_aggregation_aux')
  print(first_aggregation_aux)
  print('now')
  print(str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))'''
  try:
    if update_queue_flag_agg:
      first_aggregation_aux = update_first_aggregation_aux()
      update_queue_flag_agg = False
    if first_aggregation_aux != None and str(first_aggregation_aux) <= str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")):
      # Add to execution queue
      metric = list(wait_queue_agg.get())
      # Delete old metric
      while metric in aggregation_queue.queue:
        #print('DELETE AGGREGATION -> ' + str(metric[4]) + ' -> ' + str(metric[0]))
        del aggregation_queue.queue[aggregation_queue.queue.index(metric)]
      aggregation_queue.put(tuple(metric))
      # Add next to wait queue
      sec_to_add = convert_to_seconds(metric[14])
      metric[0] = metric[0] + relativedelta(seconds=sec_to_add)
      wait_queue_agg.put(tuple(metric))
      
      first_aggregation_aux = update_first_aggregation_aux()
    return
  except Exception as e:
    print('Timeloop agg -> ' + str(e))
    return -1
t2.start(block=False)

# ----------------------- MAIN APP -------------------------------#
# ----------------------------------------------------------------#

app = FastAPI()

@app.on_event("shutdown")
def shutdown_event():
  print('exit')
  global metrics_queue
  global wait_queue
  global aggregation_queue
  global wait_queue_agg
  metrics_queue.join()
  wait_queue.join()
  wait_queue_aggregation.join()
  aggregation_queue.join()
  #Close connection db
  close_connection()
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
  global update_queue_flag_agg
  for metric in config.metrics:
    if metric.aggregation_method != None and metric.aggregation_method.upper() not in agg_options:
      return JSONResponse(status_code=404, content={"status": "Error", "message": "Aggregation step options is "+str(agg_options)+"."})
    if metric.step_aggregation != None and metric.step_aggregation[-1] not in step_options and metric.step[-1] not in step_options:
      return JSONResponse(status_code=404, content={"status": "Error", "message": "Step and step aggregation options is "+str(step_options)+"."})
  if config.timestamp_start == None:
    config.timestamp_start = datetime.datetime.now()
  elif config.timestamp_start < datetime.datetime.now() - relativedelta(minutes=1):
    return JSONResponse(status_code=404, content={"status": "Error", "message": "Timestamp start need to be after current now."})
  if config.timestamp_end != None and config.timestamp_start > config.timestamp_end:
    return JSONResponse(status_code=404, content={"status": "Error", "message": "Timestamp start need to be after timestamp end."})
  # Save config in database
  resp = add_config(config)
  print(resp)
  if resp == -1:
    return JSONResponse(status_code=404, content={"status": "Error", "message": "Error in create config in database."})
  update_queue_flag = True
  update_queue_flag_agg = True
  info_log(200, f'Monitoring spec successfully created by operator {config.tenant_id}')
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
  update_queue_flag_agg = True
  info_log(200, f'Monitoring spec {config_id} successfully updated')
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
  update_queue_flag_agg = True
  info_log(200, f'Monitoring spec {config_id} successfully enabled')
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
  update_queue_flag_agg = True
  info_log(200, f'Monitoring spec {config_id} successfully disabled')
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
  update_queue_flag_agg = True
  info_log(200, f'Monitoring spec {config_id} successfully deleted')
  return Response(status_code=HTTP_204_NO_CONTENT)
