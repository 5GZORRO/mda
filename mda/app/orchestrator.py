from .main import *

class Orchestrator():
    
    wait_queue = PriorityQueue()
    metrics_queue = PriorityQueue()
    first_metric_aux = None
    update_queue_flag = False

    # Update first metric to read
    def update_first_metric_aux(self):

        if self.wait_queue.empty():
            return None
        aux = self.wait_queue.get()
        self.wait_queue.put(aux)

        self.first_metric_aux = aux[0]

        return aux[0]

    def request_orchestrator(self, metric_name, resourceID, next_run_at, tenantID, transactionID, networkID, kafka_topic, aggregation, metric_id, monitoring_endpoint, instanceID, productID):
        
        try:
            osm_headers = {
              "X-Gravitee-Api-Key": OSM_KEY
            }
            query_params = {
              'query': metric_name,
              'time': str(next_run_at).replace(' ', 'T') + 'Z'
            }
            response = requests.get(monitoring_endpoint, params=query_params, headers=osm_headers)
            code = response.status_code
            resp = response.text
            if response.status_code != 200:
                info_log(400, "Request to OSM not sucessful: "+str(code)+" - "+str(resp))
                #print(f'Error: Request to OSM not successful')
                return('Error in fetching data!', 200)
            json_data = json.loads(resp)
            info_log(None, f'Response from OSM: {resp}')
            metric_value = json_data["data"]["result"][0]["value"][1]
            
            if aggregation != None:
                #Save value in db
                insert_metric_value(metric_id, metric_value, next_run_at)
            else:
                if json_data["data"]["result"] != []:
                    
                    # Create JSON object that will be sent to DL Kafka Topic
                    monitoringData = {
                        "metricName" : json_data["data"]["result"][0]["metric"]["__name__"],
                        "metricValue" : metric_value,
                        "resourceID" : resourceID,
                        "instanceID": instanceID,
                        "productID": productID,
                        "timestamp" : str(next_run_at)
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
                    send_kafka(data, dataHash, kafka_topic)
                    print('SEND DATA-> '+str(next_run_at)+' -> '+ str(metric_value), flush=True)
            return 1

        except Exception as e:
            print('request_orchestrator-> ' + str(e))
            info_log(400, 'Erro in request_orchestrator: ' + str(e))
            return 0
    
    def check_waiting_metrics(self):

        while True:

            if self.update_queue_flag:
                self.first_metric_aux = self.update_first_metric_aux()
                self.update_queue_flag = False
            
            if self.first_metric_aux != None and str(self.first_metric_aux) <= str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")):
                # Add to execution queue
                metric = list(self.wait_queue.get())
                #print('ADD METRIC -> ' + str(metric[5]) + ' -> ' + str(metric[0]))
                self.metrics_queue.put(tuple(metric))
                # Delete old metric
                sec_to_add = convert_to_seconds(metric[2])
                metric[0] = metric[0] - relativedelta(seconds=sec_to_add)
                #print('METRIC -> ' + str(metric[5]) + ' -> ' + str(metric[0]))
                while tuple(metric) in self.metrics_queue.queue:
                    #print('DELETE METRIC -> ' + str(metric[5]) + ' -> ' + str(metric[0]))
                    del self.metrics_queue.queue[self.metrics_queue.queue.index(tuple(metric))]
                # Add next to wait queue
                metric[0] = metric[0] + relativedelta(seconds=sec_to_add*2)
                #print('WAIT METRIC -> ' + str(metric[5]) + ' -> ' + str(metric[0]))
                self.wait_queue.put(tuple(metric))
                
                self.first_metric_aux = self.update_first_metric_aux()
        return
