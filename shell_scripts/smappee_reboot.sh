#!/bin/bash
echo 'Login to smappee'
curl -X POST -H "Accept: application/json" -H "Content-Type: application/json" --data 'admin' http://192.168.8.113/gateway/apipublic/logon
echo 'Reboot energy monitor'
curl -X GET -H "Accept: application/json" -H "Content-Type: application/json" http://192.168.8.113/gateway/apipublic/restartSmappee?action=2
echo 'DONE'
exit 0