#!/usr/bin/env python3
# -*- coding:utf-8 -*-

import threading
import json
import requests
import traceback
from pyokapi import *
from thriftpy.rpc import make_client
from thriftpy.transport import TFramedTransportFactory

try:
    builtins = __import__('__builtin__')
except ImportError:
    import builtins


class SyncOutput():
    def __init__(self, resp):
        self.resp = resp

    def get(self):
        return self.resp

    def __str__(self):
        return str(self.resp)


def _norm(result):
    result.headers = result.headers if result.headers else {}
    content_type = result.headers.get("Content-Type", "")
    if content_type == "application/json":
        if type(result.body) == bytes:
            result.body = result.body.decode()
        result.body = json.loads(result.body)
        if isinstance(result.body, dict):
            result.body = edict(result.body)
    return result


def _InvokeService(uri, method='get', args=None, headers=None, body=None):
    headers = edict(headers) if headers else edict({})
    args = edict(args) if args else edict({})

    seg = uri.split('/')
    remote_id = '.'.join(seg[:3])
    api_path = '/'.join(seg[3:])

    print("api id: %s, api path: %s" % (remote_id, api_path), headers)
    if remote_id != 'okapi.services.1':
        s_info = _InvokeService('okapi/services/1/%s/deploy/select' % remote_id).get()
        if s_info.code == 200:
            print('get service address success:', s_info.body)
            _host = s_info.body.host
            _port = s_info.body.port
        else:
            print('get service address fails, %s, %s' % (s_info.code, s_info.body))
            return SyncOutput(s_info)
    else:
        _host = OKAPI_HOST
        _port = OKAPI_PORT
    try:
        if isinstance(body, dict) or isinstance(body, list):
            print('dict true', headers)
            headers["Content-Type"] = "application/json"
            body = json.dumps(body).encode()

        print('request args: ', args)
        for arg in args:
            val = str(args[arg])
            setattr(args, arg, val)

        client = make_client(okapi_thrift.InvokeService, _host, _port, trans_factory=TFramedTransportFactory())
        result = client.InvokeAPI(api_path, method, args, headers, body)
        print('_invoke result: ', result)
        result = _norm(result)
        return SyncOutput(result)

    except:
        traceback.print_exc()
        resp = okapi_thrift.Response(code=600, body='connection fails')
        return SyncOutput(resp)


def _ForwordService(uri, method='get', args=None, headers=None, body=None):
    print('forward service: %s' % uri)
    method = method.upper()
    headers = headers if headers else {}
    args = args if args else {}
    if body and (method == 'GET' or method == 'DELETE'):
        body = None
    elif (method == 'POST' or method == 'PUT') and not body:
        body = ''
    try:
        if isinstance(body, dict) or isinstance(body, list):
            body = json.dumps(body)
            headers["Content-Type"] = "application/json"

        resp = getattr(requests, method.lower())(url=uri, params=args, headers=headers, data=body)
        rsp = okapi_thrift.Response(code=resp.status_code, headers=resp.headers, body=resp.content)
        print("success %s: %s" % (uri, rsp.code))
        rsp = _norm(rsp)
        return SyncOutput(rsp)
    except:
        traceback.print_exc()
        resp = okapi_thrift.Response(code=602, body='forward service request fails: %s' % traceback.format_exc())
        return SyncOutput(resp)


def InvokeService(uri, method='get', args=None, headers=None, body=None):
    if uri.startswith('http'):
        future = _ForwordService(uri, method, args, headers, body)
    else:
        future = _InvokeService(uri, method, args, headers, body)
    return future


builtins.InvokeService = InvokeService

if __name__ == '__main__':

    def test():
        for i in range(10):
            print('invoke %s, thread: %s' % (i, threading.current_thread()))
            c = InvokeService('http://192.168.0.101:3636/containers/json')
            print(c.get())
            # test()


    threading.Thread(target=test).start()
    # ioloop.IOLoop.current().start()
    # time.sleep(100)
    # time.sleep(3)
    # print(c.result())
    # lst = InvokeService('okapi/services/1/services/41234fasdfa/deploy', method = 'post', source_id = "okapi/client")
    # print(lst)
