from .main import *

def info_log(status, message):
	logging.critical('"status": "'+str(status)+'", "message": "'+message+'"')

def validate_uuid4(uuid_string):
  try:
    uuid.UUID(uuid_string).hex
  except ValueError:
  	return False
  return True

def send_kafka(data, dataHash, kafka_topic):
  try:
    payload_encoded = {k: str(v).encode('utf-8') for k, v in dataHash.items()}
    hashData = {k: hashlib.sha256(v).hexdigest() for k,v in payload_encoded.items()}
    #info_log(None, f'Raw Data: {data} \nHashed Data: {hashData}')

    # public and private keys
    public_key = public_private_keys[data["operatorID"]]["public_key"]
    private_key = public_private_keys[data["operatorID"]]["private_key"]
  
    dataHashEncrypt = {rsa.encrypt(k.encode(), private_key): rsa.encrypt(v.encode(), private_key) for k,v in hashData.items()}
    #info_log(None, f'Signup Data: {dataHashEncrypt}')
  
    producer = KafkaProducer(bootstrap_servers=[KAFKA_HOST+':'+KAFKA_PORT], value_serializer=lambda x: json.dumps(x).encode('utf-8'), api_version=(0,10,1))
    producer.send(kafka_topic, key=list(dataHashEncrypt.values())[0],  value=data)
    info_log(200, f'Post metric {data["monitoringData"]["metricName"]}, from operator {data["operatorID"]}, into DL Kafka Topic {kafka_topic} [Post Time: {data["monitoringData"]["timestamp"]}]')
    return 1
  except Exception as e:
    info_log(400, 'Erro in request_orchestrator: ' + str(e))
    return 0

# Worker thread function
<<<<<<< HEAD
<<<<<<< HEAD
def queue_consumer(thread_identifier, queue, flag_agg, orchestrator, aggregator):
  try:
    while True:
      next_item = queue.get()
      
      if next_item[3] == None or next_item[0] <= next_item[3]:
        info_log(None, f'Start Fetching Values of Metric: {next_item[5]} (Thread Associated: {thread_identifier})')
        if flag_agg == 1:
=======
=======
>>>>>>> dd49afda5b88a677ffeeb1d0252ab8efd59f6e13
def queue_consumer(i, q, f, orchestrator, aggregator):
  try:
    while True:
      next_item = q.get()
      
      if next_item[3] == None or next_item[0] <= next_item[3]:
        info_log(None, f'Start Fetching Values of Metric: {next_item[5]} (Thread Associated: {i})')
        if f == 1:
<<<<<<< HEAD
>>>>>>> dd49afda5b88a677ffeeb1d0252ab8efd59f6e13
=======
>>>>>>> dd49afda5b88a677ffeeb1d0252ab8efd59f6e13
          #Send aggregation
          info_log(None, f'{datetime.datetime.now()} - UC1: Aggregating values from metric: {next_item[5]} (Step Aggregation Associated: {next_item[14]})')
          aggregator.send_aggregation(next_item[5], next_item[12], next_item[13], next_item[0], next_item[11], next_item[8], next_item[10], next_item[9], next_item[7], next_item[4], next_item[15], next_item[14])
          update_aggregation(next_item[4], next_item[0])
        
        else:
          #Send metric
          orchestrator.request_orchestrator(next_item[5], next_item[12], next_item[13], next_item[0], next_item[11], next_item[8], next_item[10], next_item[9], next_item[7], next_item[4])
          info_log(None, f'{datetime.datetime.now()} - UC2: Fetching values from OSM, metric: {next_item[5]} (Step Associated: {next_item[2]}')
          update_next_run(next_item[4], next_item[0])

<<<<<<< HEAD
<<<<<<< HEAD
      queue.task_done()
=======
      q.task_done()
>>>>>>> dd49afda5b88a677ffeeb1d0252ab8efd59f6e13
=======
      q.task_done()
>>>>>>> dd49afda5b88a677ffeeb1d0252ab8efd59f6e13
  except Exception as e:
    print(e)

def delete_old_metric(metric_id, queue):

  index = True
  while(index):
    index = False
    if queue == 0:
      for i in range(len(orchestrator.metrics_queue.queue)):
        if orchestrator.metrics_queue.queue[i][4] == metric_id:
          #print('DELETE METRIC -> ' + str(datetime.datetime.now()) + ' -> ' + str(metric_id))
          del orchestrator.metrics_queue.queue[i]
          index = True
          break
    else:
      for i in range(len(aggregator.aggregation_queue.queue)):
        if aggregator.aggregation_queue.queue[i][4] == metric_id:
          #print('DELETE AGG -> ' + str(datetime.datetime.now()) + ' -> ' + str(metric_id))
          del aggregator.aggregation_queue.queue[i]
          index = True
          break
<<<<<<< HEAD
<<<<<<< HEAD
  return
=======
  return
>>>>>>> dd49afda5b88a677ffeeb1d0252ab8efd59f6e13
=======
  return
>>>>>>> dd49afda5b88a677ffeeb1d0252ab8efd59f6e13
