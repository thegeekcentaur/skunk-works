# Problem Statement

As an engineering organization, we need various application teams to interface with Kafka (while sending/consuming data) in a standardized and consistent way, so that

- each team does not have to build or implement their own Kafka producer/subscriber
- each team can on-board to the kafka easily without deep Kafka experience
- there is a uniform contract for each kind of messages being exchanged across different products ancillary to the kafka

In order to achieve this, we want to 

- **abstract** the Kafka layer to hide its underlying/deeper technical aspects
- enable the teams to create/define their desired message structure (aka **contracts**) and **version** them as necessary, and maintain these as **registry** (for any other team to find and use), in an industry-standard way
- furnish easy installables/libraries along with wrapper code for producer and subscriber for each team


# Design Decisions/Approach

- Team A creates a schema file and sends it to the registry. Example - 
```json
{
  "type": "record",
  "name": "UserSignupEvent",
  "namespace": "com.myorg.myteam.events",
  "fields": [
    {"name": "userId", "type": "string"},
    {"name": "email", "type": "string"},
    {"name": "signupTimestamp", "type": "long"},
    {"name": "source", "type": "string"}
  ]
}
```
- Team B browses the artifact repository, locates the schema, imports the library (in the correspoding programming language) and implments the desired functionality (_publisher/subscriber_)
- For individual teams acting as publisher/subscriber, high level **Producer/Subscriber API** is published 

## Advantages

- Published and standardized contract management for each schema
- Dedicated version and life-cycle management for each schema
- Eliminiates the ambiguity between various teams publishing/subscribing to messages
- Centralized and decoupled schema management
- Easier to swap the underlying implementation without impacting business logic 
- Developers can focus on
    - Business logic and domain objects (UserSignupEvent)
    - Simple methods (send(), send_sync(), subscribe())
    - Type-safe code

## Assumptions

- Kakfa runs on a single node

## Out Of Scope

- Unit test cases
- CI/CD pipeline
- Support for Java
- Concurrency scenarios/race conditions
- Mapping between topics and schema
- Version format configuration
  - While Confluent Schema Registry supports for various formats (_avro, prtobuf_ etc.), it does not support semantic versioning, yet
  - The versioning provided by Schema Registry is **immutable and sequential**
  - To build a *semantic versioning* logic above the versioning, a metadata layer must be build on the `schema-manager-service`

# Technical Overview

- Proposed solution involves a **FastAPI**-based docker image which can be used to
    - Generate new schema
    - Revise an existing schema
    - Generate package/module based on the schema definition
    - List package(s)
    - Clean up package(s)
- In order to test out the rig, two additional docker images are introduced
    - `confluentinc/cp-kafka`
    - `confluentinc/cp-schema-registry`
- The Kafka image spins up a standard Kakfa broker
- The Kafka registry is used to maintain the schema versions in the standard (**Avro**) format


# Testing Instructions

- Launch docker compose
```bash
docker compose up --build
```
- Create a sample schema, and save this as `UserSignupEvent.json` at a location
```json
{
  "type": "record",
  "name": "UserSignupEvent",
  "namespace": "com.myorg.myteam.events",
  "fields": [
    {"name": "userId", "type": "string"},
    {"name": "email", "type": "string"},
    {"name": "signupTimestamp", "type": "long"},
    {"name": "source", "type": "string"}
  ]
}
```
- Open browser, and go to http://localhost:8000/docs to locate the published APIs
- Select `POST /schemas` from the list of available APIs, click on `Try it out`
    - mention `entity_name`: `UserSignupEvent`
    - select the `UserSignupEvent.json` saved earlier, as `schema_file`, and click `Execute`
    - verify that a 200 OK is received along with a response, similar to
```json
{
  "entity_name": "UserSignupEvent",
  "id": 1
}
```
- In the browser, go to http://localhost:8081/subjects and verify it shows `["UserSignupEvent"]` as an entry
- In the browser, go to http://localhost:8000/docs to locate `POST /schemas/{entity_name}/generate` and click on `Try it out`
    - mention `entity_name`: `UserSignupEvent`, `version`: `1` and `language`: `python`
    - click `Execute`
    - verify that a 200 OK is received along with a link to `Download file`
    - use the downloaded file as `Pypi` package along with the wrapper code/implementation for producer/subscriber, as [documented](./docs/PYTHON-DOC.md)