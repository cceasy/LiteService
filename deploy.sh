#/bin/bash

sudo rm -rf okapi-py3/pyokapi
sudo cp -r pyokapi okapi-py3/

sudo docker build -t ls/okapi-py3 okapi-py3/
sudo docker build -t ls/flask3-uwsgi flask3-uwsgi/

sudo docker-compose build
sudo docker-compose up
