![Python](https://img.shields.io/badge/python-v3.6+-blue.svg)
[![Build Status](https://travis-ci.org/anfederico/Clairvoyant.svg?branch=master)](https://travis-ci.org/anfederico/Clairvoyant)
![Dependencies](https://img.shields.io/badge/dependencies-up%20to%20date-brightgreen.svg)
[![License](https://img.shields.io/badge/license-Apache-blue.svg)](https://opensource.org/licenses/Apache-2.0)

# MDA
This is the __5GZORRO's Monitoring Data Aggregator__ component responsible for collecting, signing and pushing monitoring data, provided by each Resource and Service Provider, towards the Data Lake. As monitoring data is presented over time, it can also be aggregated and made available in a proper manner to perform the desired analytics.

### Available endpoints
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

## Production

### Pipeline Description

We provide a confluence page available online describing the intended full pipeline (steps and parameters skeleton). Please consult it [here](https://confluence.i2cat.net/pages/viewpage.action?spaceKey=5GP&title=Monitoring+Data+Aggregator+Pipeline)

<p align="center">
  <img src="https://user-images.githubusercontent.com/32877599/113858543-c07bdc80-979b-11eb-8b52-60dbaf963d63.png" />
</p>

### Deployment Instructions
This section covers all the requirements a developer may have to deploy the MDA component.

#### Prerequisites
To run this component in production, the following actions are needed:
* Create a ".env" environment variable file from the [template](https://github.com/5GZORRO/mda/blob/main/.env_template).
* Deployment in a production environment uses a github component package. Since we are handling private packages, the first step requires the authentication of the user to get permissions. So, to acquire these permissions the following command is needed:
```
$ docker login -u <GITHUB_USER> -p <GITHUB_PASSWORD_OR_TOKEN>  docker.pkg.github.com
```
**Note:** If it is required to utilize the personal access token and you do not possess that feature, you can see [here](https://docs.github.com/en/github/authenticating-to-github/creating-a-personal-access-token).

#### Deploy components
 
##### Deploy in Docker
To build and up the container we have:
```
$ docker-compose -f docker-compose-production.yml up --build
```
 * **Note:** If you want to deploy only one component, you can use:
```
$ docker-compose -f docker-compose-production.yml up --build <component_name>
```
To stop the services, we can do:
```
$ docker-compose -f docker-compose-production.yml down
```

##### Deploy in Kubernetes
To run the Kubernetes component, we first need to create secret kubernetes with the environment variables. To do so use the following command:
```
$ kubectl create secret generic env-file --from-env-file=.env
```
Then, to run the service we can use:
```
$ kubectl apply -f kubemanifests-production.yaml
```
To stop services and clear secrets, do:
```
$ kubectl delete deployments mda postgres-mda
$ kubectl delete service mda postgres-mda
$ kubectl delete secret env-file
```

### Persistence detail

In case MDA goes down when the reload occurs, it's standard to have some data loss (no requests were made to the data source in the period that the component was down). For the still-active monitoring specs when MDA reloads, the next running fields are updated accordingly with the current time and their steps.

## Development

### Pipeline Description

For the development stage, at this point, our focus has been directed on implementing a primary version of this component, including on the pipeline, a dummy OSM, a dummy VS, and a dummy component that interacts with a python client responsible to produce data and redirect to the respective dummy Kafka topic.

<p align="center">
  <img src="https://user-images.githubusercontent.com/32877599/110475056-4ee73a80-80d8-11eb-9756-b82e3c162688.png" />
</p>

Currently, our pipeline is composed of five main steps, each one held for:
1. VS sends to MDA a __configuration__ with dynamic variables specifying the monitored metrics 
2. MDA fetches from OSM the __metric values__ 
3. Metric __aggregation__, via TimescaleDB aggregation operation (if the case)
4. __Hash/signing__ data with operator's key making use of SHA256 and RSA algorithms
5. __Inject__ data into a DL Kafka Topic

### Deployment Instructions
This section covers all the requirements a developer may have to deploy the development scenario.

#### Prerequisites
To run this component in development, we need to:
* Create the ".env" environment variable file from the [template](https://github.com/5GZORRO/mda/blob/main/.env_template).
* Install PostgreSQL database. For Ubuntu 20.04, to use the apt repository, follow these steps:
```
# Create the file repository configuration:
sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'

# Import the repository signing key:
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -

# Update the package lists:
sudo apt-get update

# Install the latest version of PostgreSQL.
sudo apt-get -y install postgresql

# If you want to install a specific version, you can use postgresql-version instead of postgresql. For example, to install PostgreSQL version 12, you use the following command:
sudo apt-get install postgresql-12

# When you installed PostgreSQL, the installation process created a user account called postgres associated with the default postgres role. To connect to PostgreSQL using the postgres role, you switch over to the postgres account on your server by typing:
sudo -i -u postgres

# It will prompt for the password of the current user. You need to provide the password and hit the Enter keyboard.
```
* Run the kafka compose with:
```
$ docker-compose -f docker-compose-kafka.yml up --build
```

#### Deploy components

##### Deploy in Docker
To build and up the container we have:
```
$ docker-compose -f docker-compose-development.yml up --build
```
 * **Note:** If you want to deploy only one component, you can use:
```
$ docker-compose -f docker-compose-development.yml up --build <component_name>
```

##### Deploy in Kubernetes
To run the Kubernetes component, we first need to create secret kubernetes with the environment variables. To do so use the following command:
```
$ kubectl create secret generic env-file --from-env-file=.env
```
Then, to run the service we can use:
```
$ kubectl apply -f kubemanifests-development.yaml
```
To stop services and clear secrets, do:
```
$ kubectl delete deployments mda postgres-mda dummy-osm-mda
$ kubectl delete service mda postgres-mda dummy-osm-mda
$ kubectl delete secret env-file
```

## API Reference

We have specified this component's API in an [openapi](https://github.com/5GZORRO/mda/blob/main/doc/openapi.json)-formated file. Please check it there.

## Licensing

This 5GZORRO component is published under Apache 2.0 license. Please see the LICENSE file for further details.

## Attributions

<img src="https://www.5gzorro.eu/wp-content/uploads/2019/11/5GZorro-D12-1024x539-copia.png" width="200" />

> This page holds an early description of MDA. This component is under the responsibility of Altice Labs, with supervision of André Gomes & Bruno Santos. Please use the GitHub issues to report bugs or contact the development team through 5GZorro's Slack channel.
