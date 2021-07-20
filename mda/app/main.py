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
logging.getLogger("uvicorn.error").setLevel(logging.CRITICAL)
logging.getLogger("kafka").setLevel(logging.CRITICAL)

from .models import *

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

  OSM_QUERY = os.environ["OSM_QUERY"]
  SPECTRUM_QUERY = os.environ["SPECTRUM_QUERY"] 
  #publicKeyOperator = os.environ["OPERATOR_PUBLIC_KEY"]
except Exception as e:
  print("Environment variable does not exists: " + str(e))
  sys.exit(0)

# Json response example
json_response_enable = {"id": "ed7683f1-b625-4b41-a32d-3e690c4c6740", "created_at": "2021-07-20T11:04:34.033627", "updated_at": "null", "transaction_id": "ab51f3e1-7b61-4f9d-85a4-9e9f366b593b", "instance_id": "21", "product_id": "10", "topic": "operator-a-in-0", "monitoring_endpoint": "http://osm:4500/monitoringData?match=metric_name&start=start_time", "timestamp_start": "2021-07-20T11:04:34.030387", "timestamp_end": null, "metrics": [{"metric_name": "availability", "metric_type": "availability", "aggregation_method": "AVG", "step": "1m", "step_aggregation": "2m", "next_run_at": "2021-07-20T11:04:34.030387", "next_aggregation": "2021-07-20T11:06:34.030387"}], "status": 1, "tenant_id": "operator-a", "parent_id": "null", "context_ids": [{"resource_id": "10", "network_slice_id": "22"}]}
json_response_disable = json_response_enable.copy()
json_response_disable['status'] = 0

agg_options = ['SUM', 'AVG', 'MIN', 'MAX', 'COUNT', 'STDDEV']

step_options = ['s', 'm', 'h', 'd', 'w']

# public and private keys by tenant
public_private_keys = {}

# Metrics
num_fetch_threads = NUM_READING_THREADS

#Aggregations
num_fetch_threads_agg = NUM_AGGREGATION_THREADS

from .database import *
from .utils import *
from .orchestrator import *
from .aggregator import *

orchestrator = Orchestrator()
aggregator = Aggregator()

# --------------------- START SCRIPT -----------------------------#
# ----------------------------------------------------------------#
# Load database metrics to wait queue
load_database_metrics(orchestrator, aggregator)

# Update first metric/aggregation to read
orchestrator.update_first_metric_aux()
aggregator.update_first_aggregation_aux()

# Set up threads
for i in range(num_fetch_threads):
	worker = Thread(target = queue_consumer, args = (i, orchestrator.metrics_queue, 0, orchestrator, aggregator))
	worker.setDaemon(True)
	worker.start()
 
for i in range(num_fetch_threads_agg):
	worker = Thread(target = queue_consumer, args = (i, aggregator.aggregation_queue, 1, orchestrator, aggregator))
	worker.setDaemon(True)
	worker.start()

'''
# waiting for metrics and aggregations
worker_metrics = Thread(target = orchestrator.check_waiting_metrics, args = ())
worker_metrics.setDaemon(True)
worker_metrics.start()

worker_aggregations = Thread(target = aggregator.check_waiting_aggregations, args = ())
worker_aggregations.setDaemon(True)
worker_aggregations.start()
'''

# Check waiting metrics
tl = Timeloop()
logging.getLogger("timeloop").setLevel(logging.CRITICAL)
@tl.job(interval=timedelta(seconds=0.01))
def check_waiting_metrics():
  if orchestrator.update_queue_flag:
    orchestrator.first_metric_aux = orchestrator.update_first_metric_aux()
    orchestrator.update_queue_flag = False

  if orchestrator.first_metric_aux != None and str(orchestrator.first_metric_aux) <= str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")):
    # Add to execution queue
    metric = list(orchestrator.wait_queue.get())
    #print('ADD METRIC -> ' + str(metric[5]) + ' -> ' + str(metric[0]))
    orchestrator.metrics_queue.put(tuple(metric))
    # Delete old metric
    sec_to_add = convert_to_seconds(metric[2])
    metric[0] = metric[0] - relativedelta(seconds=sec_to_add)
    #print('METRIC -> ' + str(metric[5]) + ' -> ' + str(metric[0]))
    while tuple(metric) in orchestrator.metrics_queue.queue:
      #print('DELETE METRIC -> ' + str(metric[5]) + ' -> ' + str(metric[0]))
      del orchestrator.metrics_queue.queue[orchestrator.metrics_queue.queue.index(tuple(metric))]
    # Add next to wait queue
    metric[0] = metric[0] + relativedelta(seconds=sec_to_add*2)
    #print('WAIT METRIC -> ' + str(metric[5]) + ' -> ' + str(metric[0]))
    orchestrator.wait_queue.put(tuple(metric))

    orchestrator.first_metric_aux = orchestrator.update_first_metric_aux()
  return
tl.start(block=False)

# Check waiting metrics
t2 = Timeloop()
logging.getLogger("timeloop").setLevel(logging.CRITICAL)
@t2.job(interval=timedelta(seconds=0.01))
def check_waiting_aggregations():
  if aggregator.update_queue_flag_agg:
    aggregator.first_aggregation_aux = aggregator.update_first_aggregation_aux()
    aggregator.update_queue_flag_agg = False

  if aggregator.first_aggregation_aux != None and str(aggregator.first_aggregation_aux) <= str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")):
    # Add to execution queue
    metric = list(aggregator.wait_queue_agg.get())
    # Delete old metric
    while metric in aggregator.aggregation_queue.queue:
      #print('DELETE AGGREGATION -> ' + str(metric[4]) + ' -> ' + str(metric[0]))
      del aggregator.aggregation_queue.queue[aggregator.aggregation_queue.queue.index(metric)]
    aggregator.aggregation_queue.put(tuple(metric))
    # Add next to wait queue
    sec_to_add = convert_to_seconds(metric[13])
    metric[0] = metric[0] + relativedelta(seconds=sec_to_add)
    aggregator.wait_queue_agg.put(tuple(metric))

    aggregator.first_aggregation_aux = aggregator.update_first_aggregation_aux()

  return
t2.start(block=False)

# ----------------------- MAIN APP -------------------------------#
# ----------------------------------------------------------------#

app = FastAPI()

@app.on_event("shutdown")
def shutdown_event():
  print('exit')
  orchestrator.metrics_queue.join()
  orchestrator.wait_queue.join()
  aggregator.wait_queue_aggregation.join()
  aggregator.aggregation_queue.join()
  #Close connection db
  close_connection()
  return

# ----------------- REST FASTAPI METHODS -------------------------#
# ----------------------------------------------------------------#

from .endpoints import *
