#/bin/bash

sudo docker kill $(sudo docker ps -q)
sudo docker rm --force $(sudo docker ps -aq)
