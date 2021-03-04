from fastapi import FastAPI
import uuid, random, requests, json, hashlib, os, rsa
from Crypto.PublicKey import RSA
from pydantic import BaseModel
from typing import Optional
from kafka import KafkaProducer

'''
Timestamp final and timestamp step for each metric -> individual requests? 
'''

class Data(BaseModel):
    businessID: str
    topic: str
    sliceID: int
    metrics: list
    timestamp: str
    timestamp_final: Optional[str] = None
    step: Optional[str] = None

app = FastAPI()

def generate_url_DL():
    url = ["https://api.mocki.io/v1/4c714e05", "https://api.mocki.io/v1/89f5fb80", "https://api.mocki.io/v1/9b306fab"]
    headers = {
            'Content-Type': 'application/json'
    }

    print('test')
    # Random distribution with weights
    request_types=['201','404','500']
    option = random.choices(request_types, weights=[0.9, 0.09, 0.01], k=1)
    print(option)
    if option == ['201']:
        st = 0
    elif option == ['404']:
        st = 1
    else:
        st = 2
    print("option:"+str(st))
    return url[st]



@app.post("/set/")
async def set_param(data: Data):
    global config 
    config = data
    # print(config)
    # print(type(config))
    # print(config.businessID)
    # print(config.metrics)
    print(config.timestamp)
    # print(config.metrics[0])
    # print(config.metrics[0]['metricName'])
    # print(len(config.metrics))
    return data if data != None else "Config not received by MDA"

@app.get("/dummyData")
async def root():
    global config 
    print(config)
    print(config.timestamp)
    request_metrics = ''
    for i in range(len(config.metrics)):
        metric = "match="+config.metrics[i]['metricName']+"&"
        request_metrics += metric
    request_metrics = request_metrics + "start=" + config.timestamp.replace('"','')
    if config.timestamp_final != None:
        request_metrics = request_metrics + "&end=" + config.timestamp_final
    if config.step != None:
        request_metrics = request_metrics + "&step=" + config.step

    endpoint = 'http://osm:4500/dummyData?'
    request_url = endpoint + request_metrics

    # request get metric values from OSM
    print(request_url)
    
    resp = requests.get(request_url)
    print(resp)
    print(resp.status_code)
    if resp.status_code != 200:
        return ('Error in fetching data!', 200)
    print(resp)
    print(type(resp))
    print(resp.text)
    

    resp = {"status":"success","data":{"resultType":"matrix","result":[{"metric":{"__name__":"cpu_utilization","job":"prometheus","instance":"http://5gzorro_osm.com"},"values":[[1435781430.781,0.45],[1435795830.781,0.51],[1435810230.781,0.69],[1435824630.781,0.35],[1435839030.781,0.26],[1435853430.781,0.71],[1435867830.781,0.22]]},{"metric":{"__name__":"ram_utilization","job":"prometheus","instance":"http://5gzorro_osm.com"},"values":[[1435781430.781,0.52],[1435795830.781,0.61],[1435810230.781,0.07],[1435824630.781,0.61],[1435839030.781,0.21],[1435853430.781,0.11],[1435867830.781,0.17]]}]}}
   
    # falta definir a environment variable na máquina
    publicKeyOperator = os.environ.get("OPERATOR_PUBLIC_KEY")

    # signup data
    print("Operator public key to encrypt data: ", publicKeyOperator)
    payload_encoded = {k: str(v).encode('utf-8') for k,v in resp.items()}
    hashData = {k: hashlib.sha256(v).hexdigest() for k,v in payload_encoded.items()}
    print(hashData)
    print(type(hashData))

    print("Encrypting data with public key")
    pKey = RSA.importKey(publicKeyOperator)
    print(pKey)

    dataHashEncrypt =  {k: rsa.encrypt(v.encode(), pKey) for k,v in hashData.items()}
    print(dataHashEncrypt)

    # o que vai no request? na tabela 5.3 diz que manda MonitoringData (json) e o DataHash
    # response = requests.request("POST", url[st], headers=headers, data=json.dumps(dataHashEncrypt))
    # print(response)
    url = generate_url_DL()
    headers = {
            'Content-Type': 'application/json'
    }
    response = requests.request("POST", url, headers=headers, data=json.dumps(resp))
    print(response)

    if response.status_code == 201:
        # Data Lake Kafka Topic
        producer = KafkaProducer(bootstrap_servers=['kafka:9092'], value_serializer=lambda x:json.dumps(x).encode('utf-8'), api_version=(0,10,1))
        print("send to DL Topic")
        data = {'counter':2}
        producer.send('topic_test', value=data)
        #producer.send('topic_test', value=dataHashEncrypt)
        return "Pipeline completed"
    else:
        return ('Error in send data to Data Lake!', 200)

