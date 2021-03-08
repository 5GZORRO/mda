![Python](https://img.shields.io/badge/python-v3.6+-blue.svg)
[![Build Status](https://travis-ci.org/anfederico/Clairvoyant.svg?branch=master)](https://travis-ci.org/anfederico/Clairvoyant)
![Dependencies](https://img.shields.io/badge/dependencies-up%20to%20date-brightgreen.svg)
[![License](https://img.shields.io/badge/license-Apache-blue.svg)](https://opensource.org/licenses/Apache-2.0)

# mda
This is the __5GZORRO's Monitoring Data Aggregator__ component responsible for collecting, sign and push monitoring data, provided by each Resource and Service Provider, towards the Data Lake. As monitoring data is presented over time, it can also be aggregated and made available in a proper manner to perform the desired analytics.

## Production
This section will be available later on. For now, we tender a confluence page available online describing the intended full pipeline (steps and parameters skeleton). Consult it [here](https://confluence.i2cat.net/pages/viewpage.action?spaceKey=5GP&title=Monitoring+Data+Aggregator+Pipeline)

## Development

### Pipeline Description

For the development stage, at this point, our focus has been on implementing a primary version of this component including on the pipeline a dummy OSM, a dummy VS, and a dummy component that interacts with a python client responsible to produce data and redirect to the respective dummy Kafka topic.

<p align="center">
  <img src="https://user-images.githubusercontent.com/32877599/110141979-96668180-7dcd-11eb-85f8-c0c066a34ab1.png" />
</p>

Currently, our pipeline is composed of five main steps, each one held for:
* VS sends to MDA a __configuration__ with dynamic variables specifying the monitored metrics 
* MDA fetches from OSM the __metric values__
* Metric __aggregation__, via Prometheus python client
* __Hash/signing__ data with operator's public key making use of SHA256 and RSA algorithms
* __Inject__ data into a DL Kafka Topic

### Supported Endpoints
The following table displays the endpoints used in the development scenario:

**Component**|**Endpoint**|**Description**|**Method**
:----|:----|:----|:----
Vertical Slicer|`http://<IP>:3700/sendConfig`|**Send the settings** for get data from OSM and send to Kafka Topics| POST
MDA|`http://mda:4000/set`|**Accepts the settings** for get data from OSM and send to Kafka Topics| POST
MDA|`http://<IP>:4000/dummyData`|**Get data** from OSM and send to Kafka Topics| GET
OSM|`http://osm:4500/dummyData`|**Send metrics data by timeline** requested by MDA| GET
Kafka Topics|`kafka:9092`|**Accepts metrics data for topic**| KafkaProducer

### Deployment Instructions
This section covers all the needs a developer has to get deployment of the development scenario.

#### Prerequisites
For the signing step, described earlier, we need a public key. Therefore we need to set the operator's public key as an environment variable.
```
$ export OPERATOR_PUBLIC_KEY=<PUBLIC_KEY>
```
#### Deploy components
The components configuration is built in a docker-compose. Since we are handling private packages, the first step requires the authentication of the user to get permissions. So, to acquire these permissions the following command is needed:
```
$ docker login -u <GITHUB_USER> -p <GITHUB_PASSWORD_OR_TOKEN>  docker.pkg.github.com
```
 * **Note:** If it is required to utilize the personal access token and you do not possess that feature, you can see [here](https://docs.github.com/en/github/authenticating-to-github/creating-a-personal-access-token).

Then, for build and up the docker compose we have:
```
$ docker-compose -f docker-compose-development.yml up --build
```
 * **Note:** If you want to deploy only one component, you can use:
```
$ docker-compose -f docker-compose-development.yml up --build <component_name>
```

## API Reference

We have specified this component's API in an openapi-formated file. Please check it there.

## Licensing

This 5GZORRO component is published under Apache 2.0 license. Please see the LICENSE file for further details.

## Attributions

<img src="https://www.5gzorro.eu/wp-content/uploads/2019/11/5GZorro-D12-1024x539-copia.png" width="200" />

> This page holds the first description of the MDA component. This component is the responsibility of Altice Labs, under the supervision of José Bonnet. Please use the GitHub issues to report bugs or contact the development team through Slack channel
