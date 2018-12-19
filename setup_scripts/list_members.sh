#!/bin/bash

HOSTS=(172.31.92.226 172.31.91.28 172.31.93.186 172.31.80.225)
ENDPOINTS=${HOSTS[0]}:2379,${HOSTS[1]}:2379,${HOSTS[2]}:2379,${HOSTS[3]}:2379

~/etcd/bin/etcdctl --endpoints=$ENDPOINTS member list
