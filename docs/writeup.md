# Initial Project Write-Up
Alan Wilms & Yunhua Zhao

Presentation: https://docs.google.com/presentation/d/1ImeHJhHPahrQfVoY1fF_rFYDERRNPAMrUJWpCoDWeF8/edit?usp=sharing

## Project Description:

The goal is to create an end-to-end encrypted chat application using ZMQ with a asynchronous socket architecture. This will allow the messages to be exchanged and delivered nearly instaneously between multiple people in one or more group chats. We will use the etcd database framework to store messages and simultaneously function as a broker for the publisher-subscriber model. The encryption will allow the messages to be transmitted safely and securely, and it will be implemented using the CurveZMQ library. The user interface will be accessible via a text-based interface on the command line that connects to the server and will not only display the past chat messages with the date and time but also allow the input of new messages. These past messages would be stored in the etcd database. When clients reconnect, the local versions of the database would be reconciled to maintain consistency. A web application will be a monitoring dashboard that will display the current status of the server and any client connections in the form of graphs. If there is some network failure that halts the communication between the client and the server, the client will automatically attempt to reconnect while also notifying the user. Lastly, some inherent fault tolerance will be built in, but a later reliability analysis will find the weak points and offer a vision for an improved system for the future.

## Key features:
* Ability to start multiple chats
* Ability for multiple people to connect to each chat (group chat)
* Chat history (with timestamps)
  * Users that are added later will see the full history
* Simple application  
  * Text UI for displaying chat history and sending a new message
  * Separate web application for status monitoring
* Robust error handling for network failure
  * Automatic reconnection attempts
* Server-side status monitoring for network failures

## Preliminary languages, frameworks, and libraries:
* Python with ZMQ, and possibly some GUI library (client and server)
* etcd (broker, chat history)
* InfluxDB, Grafana (server status monitoring)

## Deliverables:
* Client chat application
* System block diagram
* Reliability analysis
  * Estimation of system reliability
  * Fault-tree analysis
  * Failure modes effect and criticality analysis
  * Future improvements (description of future revisions for increased reliability and fault tolerance)
  
**Note:** These are the initial goals - the implementation details are subject to change at any time throughout the development process.
