# -*- coding:utf-8 -*-

import thriftpy
import os
from easydict import EasyDict as edict


dirname = os.path.dirname(__file__)

okapi_thrift = thriftpy.load(os.path.join(dirname, "okapi.thrift"), module_name="okapi_thrift")

MONGO_HOST = os.environ.get('MONGO_HOST', 'mongo')
MONGO_PORT = int(os.environ.get('MONGO_PORTS', 27017))

OKAPI_HOST = os.environ.get('OKAPI_HOST', 'okapi')
OKAPI_PORT = int(os.environ.get('OKAPI_PORTS', 23241))

FILE_DATA_PATH = os.environ.get("FILE_DATA_PATH", "/data/storage/")

CONTAINER = os.environ.get('CONTAINER', '')

from pyokapi import client
