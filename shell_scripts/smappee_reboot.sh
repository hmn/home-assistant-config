#!/bin/bash
curl -X POST -H "Accept: application/json" -H "Content-Type: application/json" --data 'admin' http://192.168.8.113/gateway/apipublic/logon
curl -X GET -H "Accept: application/json" -H "Content-Type: application/json" http://192.168.8.113/gateway/apipublic/restartSmappee?action=2
