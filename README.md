![Python](https://img.shields.io/badge/python-v3.6+-blue.svg)
[![Build Status](https://travis-ci.org/anfederico/Clairvoyant.svg?branch=master)](https://travis-ci.org/anfederico/Clairvoyant)
![Dependencies](https://img.shields.io/badge/dependencies-up%20to%20date-brightgreen.svg)
[![License](https://img.shields.io/badge/license-Apache-blue.svg)](https://opensource.org/licenses/Apache-2.0)

# mda
This is the __5GZORRO's Monitoring Data Aggregator__ component responsible for collecting, signing and pushing monitoring data, provided by each Resource and Service Provider, towards the Data Lake. As monitoring data is presented over time, it can also be aggregated and made available in a proper manner to perform the desired analytics.

## Production

### Pipeline Description

Production scenario.

<p align="center">
  <img src="https://user-images.githubusercontent.com/32877599/113858543-c07bdc80-979b-11eb-8b52-60dbaf963d63.png" />
</p>

### Deployment Instructions
This section covers all the needs a developer has to get deployment of the production mda component.

#### Prerequisites
For run this component, we need to define some environment variables in file [.env](https://github.com/5GZORRO/mda/blob/main/.env).

#### Deploy components
The components configuration is built in a docker-compose. Since we are handling private packages, the first step requires the authentication of the user to get permissions. So, to acquire these permissions the following command is needed:
```
$ docker login -u <GITHUB_USER> -p <GITHUB_PASSWORD_OR_TOKEN>  docker.pkg.github.com
```
 * **Note:** If it is required to utilize the personal access token and you do not possess that feature, you can see [here](https://docs.github.com/en/github/authenticating-to-github/creating-a-personal-access-token).

Then, for build and up the docker compose we have:
```
$ docker-compose -f docker-compose-production.yml up --build
```
 * **Note:** If you want to deploy only one component, you can use:
```
$ docker-compose -f docker-compose-production.yml up --build <component_name>
```

## Development

### Pipeline Description

For the development stage, at this point, our focus has been on implementing a primary version of this component including on the pipeline a dummy OSM, a dummy VS, and a dummy component that interacts with a python client responsible to produce data and redirect to the respective dummy Kafka topic.

<p align="center">
  <img src="https://user-images.githubusercontent.com/32877599/110475056-4ee73a80-80d8-11eb-9756-b82e3c162688.png" />
</p>

Currently, our pipeline is composed of five main steps, each one held for:
1. VS sends to MDA a __configuration__ with dynamic variables specifying the monitored metrics 
2. MDA fetches from OSM the __metric values__ 
3. Metric __aggregation__, via Prometheus python client (if the case)
4. __Hash/signing__ data with operator's key making use of SHA256 and RSA algorithms
5. __Inject__ data into a DL Kafka Topic

### Supported Endpoints
The following table displays the endpoints used in the development scenario:

**Component**|**Endpoint**|**Description**|**Method**
|:----|:----|:----
`http://<IP>:4000/settings`|Enable and send the monitoring spec with the dynamic config variables|POST
`http://<IP>:4000/settings/:id/enable`|Enable a certain monitoring spec|PUT
`http://<IP>:4000/settings/:id/disable`|Disable the current monitoring spec|PUT
`http://<IP>:4000/settings/:id`|Modify the current monitoring spec|PUT
`http://<IP>:4000/settings/:id`|Retrieve all the monitoring specs associated with a given id|GET
`http://<IP>:4000/settings`|Retrieve all the existing monitoring specs|GET
`http://<IP>:4000/settings/:id`|Delete a certain existing monitoring specs|DELETE


### Deployment Instructions
This section covers all the needs a developer has to get deployment of the development scenario.

#### Prerequisites
For run this component, we need to define some environment variables in file [.env](https://github.com/5GZORRO/mda/blob/main/.env).

#### Deploy components
For build and up the docker compose we have:
```
$ docker-compose -f docker-compose-development.yml up --build
```
 * **Note:** If you want to deploy only one component, you can use:
```
$ docker-compose -f docker-compose-development.yml up --build <component_name>
```

## API Reference

We have specified this component's API in an [openapi](https://github.com/5GZORRO/mda/blob/main/doc/openapi.json)-formated file. Please check it there.

## Licensing

This 5GZORRO component is published under Apache 2.0 license. Please see the LICENSE file for further details.

## Attributions

<img src="https://www.5gzorro.eu/wp-content/uploads/2019/11/5GZorro-D12-1024x539-copia.png" width="200" />

> This page holds the first description of the MDA component. This component is the responsibility of Altice Labs, under the supervision of José Bonnet. Please use the GitHub issues to report bugs or contact the development team through Slack channel
