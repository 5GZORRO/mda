![Python](https://img.shields.io/badge/python-v3.6+-blue.svg)
[![Build Status](https://travis-ci.org/anfederico/Clairvoyant.svg?branch=master)](https://travis-ci.org/anfederico/Clairvoyant)
![Dependencies](https://img.shields.io/badge/dependencies-up%20to%20date-brightgreen.svg)
[![License](https://img.shields.io/badge/license-Apache-blue.svg)](https://opensource.org/licenses/Apache-2.0)

# MDA
This is the _5GZORRO's Monitoring Data Aggregator_ component responsible for collecting, signing and pushing monitoring data, provided by each Resource and Service Provider, towards the Data Lake. As monitoring data is presented over time, it can also be aggregated and made available in a proper manner to perform the desired analytics.

## Prerequisites
*System Requirements*
* 4 vCPUs
* 8 GB RAM
* 20 GB Storage
* K8s containers

### 5GZORRO Module dependencies
- Network Slice and Service Orchestrator (NSSO)
- xRM
- 5GZORRO Datalake

To run this component in production, the following actions are needed:
* Create a ".env" environment variable file from the template.
* Deployment in a production environment uses a github component package. Since we are handling private packages, the first step requires the authentication of the user to get permissions. So, to acquire these permissions the following command is needed:

```python
$ docker login -u <GITHUB_USER> -p <GITHUB_PASSWORD_OR_TOKEN>  docker.pkg.github.com
```

*Note:* If it is required to utilize the personal access token and you do not possess that feature, you can see here:

## Configuration

> :warning: *For a Development stage enviroment configuration, follow the documentation ["Development Environment Configuration"](https://github.com/5GZORRO/mda/wiki/Development-Environment-Configuration)!*

### Pipeline Description

We provide a confluence page available online describing the intended full pipeline (steps and parameters skeleton). Please consult it here

<p align="center">
  <img src="https://user-images.githubusercontent.com/32877599/113858543-c07bdc80-979b-11eb-8b52-60dbaf963d63.png" />
</p>

### Deployment Instructions
This section covers all the requirements a developer may have to deploy the MDA component.
> :warning: *If you need to implement MDA components by operator, follow the documentation ["Deploy MDA by operator"](https://github.com/5GZORRO/mda/wiki/Deploy-MDA-per-Operator)!*

#### Deploy components
 
##### Deploy in Docker
To build and up the container we have:

```python
$ docker-compose -f docker-compose-production.yml up --build
```

To stop the services, we can do:

```python
$ docker-compose -f docker-compose-production.yml down
```


##### Deploy in Kubernetes
To run the Kubernetes component, we first need to create secret kubernetes with the environment variables. To do so use the following command:

```python
$ kubectl create secret generic env-file --from-env-file=.env
```

Then, to run the service we can use:

```python
$ kubectl apply -f kubemanifests-production.yaml
```

To stop services and clear secrets, do:

```python
$ kubectl delete -f kubemanifests-production.yaml
$ kubectl delete secret env-file
```


### Persistence detail

In case MDA goes down when the reload occurs, it's standard to have some data loss (no requests were made to the data source in the period that the component was down). For the still-active monitoring specs when MDA reloads, the next running fields are updated accordingly with the current time and their steps.

## API Reference
The following table displays the available endpoints:

**Endpoint**|**Description**|**Method**
|:----|:----|:----
`http://<IP>:<MDA_PORT>/settings`|Enable and send the monitoring spec with the dynamic config variables|POST
`http://<IP>:<MDA_PORT>/settings/:id/enable`|Enable a certain monitoring spec|PUT
`http://<IP>:<MDA_PORT>/settings/:id/disable`|Disable the current monitoring spec|PUT
`http://<IP>:<MDA_PORT>/settings/:id`|Modify the current monitoring spec|PUT
`http://<IP>:<MDA_PORT>/settings/:id`|Retrieve all the monitoring specs associated with a given id|GET
`http://<IP>:<MDA_PORT>/settings`|Retrieve all the existing monitoring specs|GET
`http://<IP>:<MDA_PORT>/settings/:id`|Delete a certain existing monitoring specs|DELETE

## Maintainers
*André Gomes* - Design & Development - andre-d-gomes@alticelabs.com

## License
This module is distributed under [Apache 2.0 License](LICENSE) terms.
