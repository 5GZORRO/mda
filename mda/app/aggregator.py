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

    def send_aggregation(self, metric_name, resourceID, referenceID, next_run_at, tenantID, businessID, networkID, kafka_topic, aggregation, metric_id, next_aggregation, step_aggregation):
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

            # send to kafka
            send_kafka(data, dataHash, kafka_topic)

            print('SEND AGGREGATION-> '+str(next_run_at)+' -> '+ str(value), flush=True)
            return 1
        except Exception as e:
            print('send_aggregation-> ' + str(e))
            info_log(400, 'Erro in request_aggregator: ' + str(e))
            return 0

    def check_waiting_aggregations(self):

        while True:

            if self.update_queue_flag_agg:
                self.first_aggregation_aux = self.update_first_aggregation_aux()
                self.update_queue_flag_agg = False
                
            if self.first_aggregation_aux != None and str(self.first_aggregation_aux) <= str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")):
                # Add to execution queue
                metric = list(self.wait_queue_agg.get())
                # Delete old metric
                while metric in self.aggregation_queue.queue:
                    #print('DELETE AGGREGATION -> ' + str(metric[4]) + ' -> ' + str(metric[0]))
                    del self.aggregation_queue.queue[self.aggregation_queue.queue.index(metric)]
                self.aggregation_queue.put(tuple(metric))
                # Add next to wait queue
                sec_to_add = convert_to_seconds(metric[14])
                metric[0] = metric[0] + relativedelta(seconds=sec_to_add)
                self.wait_queue_agg.put(tuple(metric))
                
                self.first_aggregation_aux = self.update_first_aggregation_aux()
        return