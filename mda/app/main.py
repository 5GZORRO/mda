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

  OSM_URL = os.environ["OSM_URL"]
  
  #publicKeyOperator = os.environ["OPERATOR_PUBLIC_KEY"]
except Exception as e:
  print("Environment variable does not exists: " + str(e))
  sys.exit(0)

# Json response example
json_response_enable = {"id": "ab51f3e1-7b61-4f9d-85a4-9e9f366b593b","created_at": "2021-03-11T11:34:00.402075","updated_at": "null","businessID": 36574564,"businessID": "business1", "topic": "test1", "networkID": 1, "tenantID": "tenant1", "referenceID": "reference1", "resourceID": "resource1","timestampStart": "2021-03-11T11:35:00","timestampEnd": "null","metrics": [{"metricName": "cpu_utilization","metricType": "float","aggregationMethod": "sum","step": "15min","step_aggregation": "1h", "next_run_at": "2021-03-11T11:45:00", "next_aggregation": "2021-03-11T12:35:00"}],"status": 1}
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

# waiting for metrics and aggregations
worker_metrics = Thread(target = orchestrator.check_waiting_metrics, args = ())
worker_metrics.setDaemon(True)
worker_metrics.start()

worker_aggregations = Thread(target = aggregator.check_waiting_aggregations, args = ())
worker_aggregations.setDaemon(True)
worker_aggregations.start()

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