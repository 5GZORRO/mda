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
        
    def get_value_orchestrator(self, monitoring_endpoint, metric_name, time):
        try:
            osm_headers = {
              "X-Gravitee-Api-Key": OSM_KEY
            }
            query_params = {
              'query': metric_name,
              'time': time
            }
            response = requests.get(monitoring_endpoint, params=query_params, headers=osm_headers)
            code = response.status_code
            resp = response.text
            if response.status_code != 200:
                info_log(400, "Request to OSM not sucessful: "+str(code)+" - "+str(resp))
                #print(f'Error: Request to OSM not successful')
                return "Error"
            json_data = json.loads(resp)
            result = json_data["data"]["result"]
            
            if len(result) == 0:
                info_log(400, 'Erro in request_orchestrator: No values to read')
                return "Error"
            
            value = result[0]["value"][1]
            try:
                metric_value = float(value)
            except:
                info_log(400, 'Erro in request_orchestrator: Value [' + str(value) + '] is an invalid numeric data')
                return "Error"
            
            info_log(200, f'Response from OSM: {resp}')
            
            return metric_value

        except Exception as e:
            print('get_value_orchestrator-> ' + str(e))
            info_log(400, 'Erro in get_value_orchestrator: ' + str(e))
            return "Error"

    def request_orchestrator(self, metric_name, resourceID, next_run_at, tenantID, transactionID, networkID, kafka_topic, aggregation, metric_id, monitoring_endpoint, instanceID, productID, producer, step):
        
        try:
            metric_value = self.get_value_orchestrator(monitoring_endpoint, metric_name, str(next_run_at).replace(' ', 'T') + 'Z')
            if metric_value == "Error":
                info_log(400, 'Erro in request_orchestrator: get_value_orchestrator invalid')
                return 0
                
            if metric_name == "osm_requests":
                # Read old value
                sec_to_add = convert_to_seconds(step)
                old_time = next_run_at - relativedelta(seconds=sec_to_add)
                old_metric_value = self.get_value_orchestrator(monitoring_endpoint, metric_name, str(old_time).replace(' ', 'T') + 'Z')
                if old_metric_value == "Error":
                    info_log(400, 'Erro in request_orchestrator: get_value_orchestrator invalid')
                    return 0

                #Diff between old value and new value
                metric_value -= old_metric_value
            
            if aggregation != None:
                #Save value in db
                insert_metric_value(metric_id, metric_value, next_run_at)
            else:
                # Create JSON object that will be sent to DL Kafka Topic
                monitoringData = {
                    "metricName" : metric_name,
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
                send_kafka(data, dataHash, kafka_topic, producer)
                print('SEND DATA-> '+str(next_run_at)+' -> '+ str(metric_value), flush=True)
            return 1

        except Exception as e:
            print('request_orchestrator-> ' + str(e))
            info_log(400, 'Erro in request_orchestrator: ' + str(e))
            return 0
