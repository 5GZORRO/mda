from .main import *

class Aggregator():
    
    wait_queue_agg = PriorityQueue()
    aggregation_queue = PriorityQueue()
    first_aggregation_aux = None
    update_queue_flag_agg = False

    # Update first aggregation to read
    def update_first_aggregation_aux(self):

        if self.wait_queue_agg.empty():
            return None
        aux = self.wait_queue_agg.get()
        self.wait_queue_agg.put(aux)

        self.first_aggregation_aux = aux[0]

        return aux[0]

    def send_aggregation(self, metric_name, resourceID, next_run_at, tenantID, transactionID, networkID, kafka_topic, aggregation, metric_id, next_aggregation, step_aggregation, instanceID, productID, producer):
        try:
            value = get_last_aggregation(metric_id, aggregation, next_run_at, step_aggregation)
            if value is None:
                info_log(400, 'Erro in send_aggregation: No values to aggregate')
                return 0
                
            # Create JSON object that will be sent to DL Kafka Topic
            monitoringData = {
                "metricName" : metric_name,
                "metricValue" : value,
                "resourceID" : resourceID,
                "instanceID": instanceID,
                "productID": productID,
                "timestamp" : str(next_run_at),
                "aggregationMethod": aggregation
            }
            
            dataHash = {
                "data" : monitoringData
            }
        
            data = {
                "operatorID" : tenantID,
                "transactionID" : transactionID,
                "networkID" : networkID
            }
            data["monitoringData"] = monitoringData

            # send to kafka
            send_kafka(data, dataHash, kafka_topic, producer)

            print('SEND AGGREGATION-> '+str(next_run_at)+' -> '+ str(value), flush=True)
            return 1
        except Exception as e:
            print('send_aggregation-> ' + str(e))
            info_log(400, 'Erro in request_aggregator: ' + str(e))
            return 0
