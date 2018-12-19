#!/bin/bash

TOKEN=token-01
CLUSTER_STATE=new

NAMES=(machine-1 machine-2 machine-3 machine-4)

HOSTS=(172.31.92.226 172.31.91.28 172.31.93.186 172.31.80.225)

CLUSTER=${NAMES[0]}=http://${HOSTS[0]}:2380,${NAMES[1]}=http://${HOSTS[1]}:2380,${NAMES[2]}=http://${HOSTS[2]}:2380,${NAMES[3]}=http://${HOSTS[3]}:2380

# Change number based on machine
THIS_NAME=${NAMES[$1]}
THIS_IP=${HOSTS[$1]}

echo "Using $THIS_NAME"

~/etcd/bin/etcd --data-dir=data.etcd --name ${THIS_NAME} \
	--initial-advertise-peer-urls http://${THIS_IP}:2380 --listen-peer-urls http://${THIS_IP}:2380 \
	--advertise-client-urls http://${THIS_IP}:2379 --listen-client-urls http://${THIS_IP}:2379 \
	--initial-cluster ${CLUSTER} \
	--initial-cluster-state ${CLUSTER_STATE} --initial-cluster-token ${TOKEN}
