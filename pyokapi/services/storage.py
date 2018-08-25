# -*- coding:utf-8 -*-

from pyokapi import *
from pymongo import Connection

import hashlib

import os
import traceback

data_path = FILE_DATA_PATH

if not data_path.endswith('/'):
    data_path = data_path + "/"
data_path = data_path + "%s"

print('file server use mongo db: %s:%s' % (MONGO_HOST, MONGO_PORT))
_db_conn = Connection(MONGO_HOST, MONGO_PORT)
_file_collection = _db_conn.okapi.file


@post("/okapi/program/<f_id>")
def save_file(f_id):
    payload = api.body
    print(type(payload))
    try:
        f_doc = _file_collection.find_one({"f_id": f_id})
        if f_doc:
            raise Exception('file already exist')

        md5 = hashlib.md5()
        md5.update(payload)

        md5 = md5.hexdigest()
        f_path = data_path % md5
        if not os.path.isfile(f_path):
            with open(f_path, "wb") as f:
                f.write(payload)
        f_doc = {"f_id": f_id, "hash": md5, "size": len(payload)}
        _file_collection.insert(f_doc)
        return 'success', 201
    except Exception as e:
        traceback.print_exc()
        return 'exception: %s' % type(e), 500


@get("/okapi/program/<f_id>")
def get_file(f_id):
    try:
        f_doc = _file_collection.find_one({"f_id": f_id})
        print(f_doc)
        if not f_doc:
            return 'file not found', 404
        else:
            f_path = data_path % f_doc["hash"]
            with open(f_path, 'rb') as f:
                return f.read(), 200, [("Content-Type", "application/octet-stream")]
    except Exception as e:
        traceback.print_exc()
        return 'exception: %s' % type(e), 500
