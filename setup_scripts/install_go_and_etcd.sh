#!/bin/bash

wget https://dl.google.com/go/go1.11.2.linux-amd64.tar.gz
tar -C /usr/local -xzf go1.11.2.linux-amd64.tar.gz

echo -e "\n\n# From Go installation\nexport PATH=$PATH:/usr/local/go/bin" >> $HOME/.profile
source $HOME/.profile

git clone https://github.com/coreos/etcd.git ~/etcd
cd ~/etcd
./build
