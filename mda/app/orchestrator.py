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
        
    def get_value_orchestrator(self, monitoring_endpoint, metric_id, metric_name, time, network_id, resource_id):
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
                #print('orchestrator:get_value_orchestrator -> Request to OSM not successful', flush=True)
                info_log(metric_id, 'ERROR', 'Error in orchestrator:get_value_orchestrator: Request to OSM not sucessful with code '+str(code)+' - '+str(resp))
                return "Error"
            json_data = json.loads(resp)
            result = json_data["data"]["result"]
            
            # Search metric value by network_slice_id or cell_id
            value = None
            for result in json_data['data']['result']:
              if 'ns_id' in result['metric'] and result['metric']['ns_id'] == str(network_id):
                value = result['value'][1]
                break
              elif 'cell_id' in result['metric'] and result['metric']['cell_id'] == str(resource_id):
                value = result['value'][1]
                break
              elif 'ns_id' not in result['metric'] and 'cell_id' not in result['metric']:
                value = result['value'][1]
                    
            if value == None:
                info_log(metric_id, 'INFO', 'Error in orchestrator:get_value_orchestrator: No values to read')
                return "Error"
            
            try:
                metric_value = float(value)
            except:
                info_log(metric_id, 'ERROR', 'Error in orchestrator:get_value_orchestrator: Value [' + str(value) + '] is an invalid numeric data')
                return "Error"
            
            info_log(metric_id, 'INFO', f'Response from OSM: {resp}')
            
            return metric_value

        except Exception as e:
            #print('orchestrator:get_value_orchestrator -> ' + str(e), flush=True)
            info_log(metric_id, 'ERROR', 'Error in orchestrator:get_value_orchestrator: ' + str(e))
            return "Error"

    def request_orchestrator(self, metric_name, resourceID, next_run_at, tenantID, transactionID, networkID, kafka_topic, aggregation, metric_id, monitoring_endpoint, instanceID, productID, producer, step):
        
        try:
            metric_value = self.get_value_orchestrator(monitoring_endpoint, metric_id, metric_name, str(next_run_at).replace(' ', 'T') + 'Z', networkID, resourceID)
            if metric_value == "Error":
                return 0
                
            if metric_name == "osm_requests":
                # Read old value
                sec_to_add = convert_to_seconds(step)
                old_time = next_run_at - relativedelta(seconds=sec_to_add)
                old_metric_value = self.get_value_orchestrator(monitoring_endpoint, metric_id, metric_name, str(old_time).replace(' ', 'T') + 'Z', networkID, resourceID)
                if old_metric_value == "Error":
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
                send_kafka(metric_id, data, dataHash, kafka_topic, producer)
                print('SEND DATA -> '+str(next_run_at)+' -> '+ str(metric_value), flush=True)
                info_log(metric_id, 'SUCCESS', 'Send data: '+str(next_run_at)+' -> '+ str(metric_value))
            return 1

        except Exception as e:
            #print('orchestrator:request_orchestrator -> ' + str(e), flush=True)
            info_log(metric_id, 'ERROR', 'Error in orchestrator:request_orchestrator: ' + str(e))
            return 0
