from .main import *

def validate_uuid4(uuid_string):
  try:
    uuid.UUID(uuid_string).hex
  except ValueError:
  	return False
  return True

def send_kafka(metric_id, data, dataHash, kafka_topic, producer):
  try:
    payload_encoded = {k: str(v).encode('utf-8') for k, v in dataHash.items()}
    hashData = {k: hashlib.sha256(v).hexdigest() for k,v in payload_encoded.items()}
    
    # public and private keys
    public_key = public_private_keys[data["operatorID"]]["public_key"]
    private_key = public_private_keys[data["operatorID"]]["private_key"]
  
    dataHashEncrypt = {rsa.encrypt(k.encode(), private_key): rsa.encrypt(v.encode(), private_key) for k,v in hashData.items()}
    
    producer.send(kafka_topic, key=list(dataHashEncrypt.values())[0],  value=data)
    info_log(metric_id, 'SUCCESS', f'Post metric {data["monitoringData"]["metricName"]}, from operator {data["operatorID"]}, into DL Kafka Topic {kafka_topic} [Post Time: {data["monitoringData"]["timestamp"]}]')
    return 1
  except Exception as e:
    #print('utils:send_kafka -> ' + str(e), flush=True)
    info_log(metric_id, 'ERROR', 'Error in utils:send_kafka: ' + str(e))
    return 0

def queue_consumer(thread_identifier, queue, flag_agg, orchestrator, aggregator, producer):
  try:
    while True:
      next_item = queue.get()
      
      if next_item[3] == None or next_item[0] <= next_item[3]:
        info_log(next_item[4], 'INFO', f'Start Fetching Values of Metric: {next_item[5]} (Thread Associated: {thread_identifier})')
        if flag_agg == 1:

          #Send aggregation
          info_log(next_item[4], 'INFO', f'{datetime.datetime.now()} - UC1: Aggregating values from metric: {next_item[5]} (Step Aggregation Associated: {next_item[0]})')
          aggregator.send_aggregation(next_item[5], next_item[12], next_item[0], next_item[11], next_item[8], next_item[10], next_item[9], next_item[7], next_item[4], next_item[14], next_item[13], next_item[15], next_item[16], producer)
          
        else:
          #Send metric
          orchestrator.request_orchestrator(next_item[5], next_item[12], next_item[0], next_item[11], next_item[8], next_item[10], next_item[9], next_item[7], next_item[4], next_item[15], next_item[16], next_item[17], producer, next_item[2])
          info_log(next_item[4], 'INFO', f'{datetime.datetime.now()} - UC2: Fetching values from OSM, metric: {next_item[5]} (Step Associated: {next_item[0]}')
          
      queue.task_done()
  except Exception as e:
    #print('utils:queue_consumer -> ' + str(e), flush=True)
    info_log(metric_id, 'ERROR', 'Error in utils:queue_consumer: ' + str(e))

def delete_old_metric(metric_id, queue):
  try:
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
    return
  except Exception as e:
    #print('utils:delete_old_metric -> ' + str(e), flush=True)
    info_log(metric_id, 'ERROR', 'Error in utils:delete_old_metric: ' + str(e))
    return -1
