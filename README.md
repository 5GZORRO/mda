![Python](https://img.shields.io/badge/python-v3.6+-blue.svg)
[![Build Status](https://travis-ci.org/anfederico/Clairvoyant.svg?branch=master)](https://travis-ci.org/anfederico/Clairvoyant)
![Dependencies](https://img.shields.io/badge/dependencies-up%20to%20date-brightgreen.svg)
[![License](https://img.shields.io/badge/license-Apache-blue.svg)](https://opensource.org/licenses/Apache-2.0)

# mda
This is the 5GZORRO's Monitoring Data Aggregator component responsible for collecting, sign and push monitoring data, provided by each Resource and Service Provider, towards the Data Lake. As monitoring data is presented over time, it can also be aggregated and made available in a proper manner to perform the desired analytics.

## Production
This section will be available later on.

## Development

### Pipeline Description

### Supported Endpoints
The following table presents the list of endpoints used in development cenary.

**Component**|**Endpoint**|**Description**|**Method**
:----|:----|:----|:----
Vertical Slicer|`http://<IP>:3700/sendConfig`|**Send the settings** for get data from OSM and send to Kafka Topics| POST
MDA|`http://mda:4000/set`|**Accepts the settings** for get data from OSM and send to Kafka Topics| POST
MDA|`http://<IP>:4000/dummyData`|**Get data** from OSM and send to Kafka Topics| GET
OSM|`http://osm:4500/dummyData`|**Send metrics data by timeline** requested by MDA| GET
Kafka Topics|`kafka:9092`|**Accepts metrics data for topic**| KafkaProducer

### NBI MDA

### Deployment Instructions
This section covers all the needs a developer to get deployment of the development cenary.

#### Prerequisites
For sign the metrics data we need a public key, so in this cenary we config this key in an environment variable.
```
$ export OPERATOR_PUBLIC_KEY=<PUBLIC_KEY>
```
#### Deploy components
The components configuration has in docker compose, so we need to build and up this compose. How we use a private packages, we need to login in docker for get permitions for this.

So, for to login in docker we has:
```
$ docker login -u <GITHUB_USER> -p <GITHUB_PASSWORD_OR_TOKEN>  docker.pkg.github.com
```
 * **Note:** If you want to use the personal access token and don´t has, you can see [here](https://docs.github.com/en/github/authenticating-to-github/creating-a-personal-access-token).

Then, for build and up the docker compose we has:
```
$ docker-compose -f docker-compose-development.yml up --build
```
 * **Note:** If you want to deploy only one component, you can use:
```
$ docker-compose -f docker-compose-development.yml up --build <component_name>
```

## Licensing

This 5GZORRO component is published under Apache 2.0 license. Please see the LICENSE file for further details.

## Attributions

<img src="https://www.5gzorro.eu/wp-content/uploads/2019/11/5GZorro-D12-1024x539-copia.png" width="200" />
