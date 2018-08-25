#!/usr/bin/env python3
# -*- coding:utf-8 -*-

import sys
import traceback
import threading
import json
from datetime import timedelta
from werkzeug.routing import Map, Rule
from werkzeug.exceptions import HTTPException

from thriftpy.tornado import make_server

from pyokapi import *

from tornado import gen, ioloop

try:
    builtins = __import__('__builtin__')
except ImportError:
    import builtins

bin_path = os.environ.get("BIN_PATH", "/home/okapi/bin")

builtins.api = threading.local()

url_map = Map()
view_functions = {}


def _decorator(method):
    def d(rule, **options):
        def decorator(f):
            endpoint = options.pop('endpoint', None)
            options["methods"] = (method,)
            # f = gen.coroutine(f)
            add_url_rule(rule, endpoint, f, **options)
            return f

        return decorator

    return d


for m in ['get', 'post', 'put', 'delete']:
    setattr(builtins, m, _decorator(m))


def _endpoint_from_view_func(view_func):
    """Internal helper that returns the default endpoint for a given
    function.  This always is the function name.
    """
    assert view_func is not None, 'expected view func if endpoint ' \
                                  'is not provided.'
    return view_func.__name__


def add_url_rule(rule, endpoint=None, view_func=None, **options):
    if endpoint is None:
        endpoint = _endpoint_from_view_func(view_func)
    options['endpoint'] = endpoint
    methods = options.pop('methods', None)

    # if the methods are not given and the view_func object knows its
    # methods we can use that instead.  If neither exists, we go with
    # a tuple of only `GET` as default.
    if methods is None:
        methods = getattr(view_func, 'methods', None) or ('GET',)
    methods = set(methods)

    # Methods that should always be added
    required_methods = set(getattr(view_func, 'required_methods', ()))

    # starting with Flask 0.8 the view_func object can disable and
    # force-enable the automatic options handling.
    provide_automatic_options = getattr(view_func,
                                        'provide_automatic_options', None)

    if provide_automatic_options is None:
        if 'OPTIONS' not in methods:
            provide_automatic_options = True
            required_methods.add('OPTIONS')
        else:
            provide_automatic_options = False

    # Add the required methods now.
    methods |= required_methods

    # due to a werkzeug bug we need to make sure that the defaults are
    # None if they are an empty dictionary.  This should not be necessary
    # with Werkzeug 0.7
    options['defaults'] = options.get('defaults') or None

    rule = Rule(rule, methods=methods, **options)
    rule.provide_automatic_options = provide_automatic_options

    url_map.add(rule)
    if view_func is not None:
        old_func = view_functions.get(endpoint)
        if old_func is not None and old_func != view_func:
            raise AssertionError('View function mapping is overwriting an '
                                 'existing endpoint function: %s' % endpoint)
        view_functions[endpoint] = view_func


class Dispatcher(object):
    def InvokeAPI(self, api_path, method, arg, headers, body):

        try:
            print(type(api_path), type(method), type(arg), type(headers), type(body))
            if sys.version_info[0] < 3:
                if isinstance(api_path, unicode):
                    api_path = api_path.encode('utf-8')
                if isinstance(method, unicode):
                    method = method.encode('utf-8')

            api_path = api_path if api_path.startswith('/') else '/%s' % api_path
            api.args = arg = edict(arg if arg else {})
            api.headers = headers = edict(headers if headers else {})

            print("invoke %s, service path: %s, method: %s" % (api_id, api_path, method))
            print("arg: %s, headers: %s" % (arg, headers))

            if headers.get("Content-Type", '') == "application/json":
                body = json.loads(body)
                if isinstance(body, dict):
                    body = edict(body)
            api.body = body
            # print('body:%s' % api.body)

            try:
                urls = url_map.bind('')
                endpoint, args = urls.match(api_path, method)
                print(endpoint)
                data = view_functions[endpoint](**args)
            except HTTPException as he:
                traceback.print_exc()
                data = he.get_description(), he.code, he.get_headers(None)
            except Exception as e:
                traceback.print_exc()
                data = 'exceptions:%s' % traceback.format_exc(), 500
            result = self.make_response(data)
            # print(result)
        except Exception as e:
            result = okapi_thrift.Response(code=602, body=traceback.format_exc(), headers={})

        return result

    @staticmethod
    def make_response(rv):

        if isinstance(rv, okapi_thrift.Response):
            return rv

        status = headers = None

        if isinstance(rv, tuple):
            body, status, headers = rv + (None,) * (3 - len(rv))
        else:
            body = "" if (rv is None or rv == '') else rv

        status = status if status else 200
        headers = headers if headers else {}

        if isinstance(headers, list):
            _headers = {}
            for k, v in headers:
                _headers[k] = v
            headers = _headers

        if isinstance(body, dict) or isinstance(body, list):
            body = json.dumps(body)
            headers["Content-Type"] = "application/json"
        else:
            if sys.version_info[0] >= 3:
                if not isinstance(body, bytes):
                    body = str(body)
            elif isinstance(body, unicode):
                body = body.encode('utf8')
            else:
                body = str(body)

        if not isinstance(body, bytes):
            body = str(body).encode('utf8')

        return okapi_thrift.Response(code=status, body=body, headers=headers)


def serve_forever(_api, _port):
    try:
        dep = {}
        __import__(_api.module_name)
        server = make_server(okapi_thrift.InvokeService, Dispatcher(), transport_read_timeout=timedelta(seconds=10))
        server.bind(_port)
        server.start(1)
        print('deploy success')

        if api_id == 'okapi/storage/1':
            resp = InvokeService("okapi/services/1/%s/deploy/%s" % (api_id.replace("/", "."), CONTAINER), method='put',
                                 args={"port": str(_port)})
            print("invoke deploy %s" % resp)
        if api_id != 'okapi/services/1':
            _api_detail = []
            for rule in url_map.iter_rules():
                ms = rule.methods - set(["OPTIONS", "HEAD"])
                _api_detail.append({'rule': rule.rule, 'methods': list(ms), 'function': rule.endpoint})
            InvokeService("okapi/services/1/%s/api" % api_id.replace("/", "."), method='post', body=_api_detail)

            dep["status"] = "running"
            dep["debug"] = ""
            dep["message"] = ""
            InvokeService("okapi/services/1/%s/deploy" % api_id.replace('/', '.'), method='put', body=dep)

        ioloop.IOLoop.instance().start()

    except Exception as e:
        traceback.print_exc()
        dep["status"] = "exited"
        dep["message"] = str(e)
        dep["debug"] = traceback.format_exc()
        if api_id != 'okapi/services/1':
            print("deploy exited: %s" % dep)
            reps = InvokeService("okapi/services/1/%s/deploy" % api_id.replace('/', '.'), method='put', body=dep)
            print(resp)


if __name__ == '__main__':

    if len(sys.argv) < 2:
        print('you must specify an api_id, usage: python3 -m okapi.server api_id [port]')
    else:
        api_id = sys.argv[1]

        if len(sys.argv) >= 3:
            _port = int(sys.argv[2])
        else:
            _port = OKAPI_PORT
        print('get infos of api: %s' % api_id)
        if api_id == 'okapi/services/1':
            _service = edict(
                {'author': 'okapi', 'name': 'services', 'version': '1', 'module_name': 'pyokapi.services.service',
                 "title": "OKAPI系统服务", "description": "查询、创建、部署服务"})
        elif api_id == 'okapi/storage/1':
            _service = edict(
                {'author': 'okapi', 'name': 'storage', 'version': '1', 'module_name': 'pyokapi.services.storage',
                 "title": "OKAPI存储服务", "description": "OKAPI存储服务"})
        else:
            try:
                _id = api_id.replace('/', '.')
                resp = InvokeService('okapi/services/1/%s' % _id).get()
                if resp.code != 200:
                    print(resp)
                    sys.exit(2)
                _service = resp.body
                _service.id = "%s/%s/%s" % (_service.author, _service.name, _service.version)

                path = "%s/%s/" % (bin_path, _service.id)

                if not os.path.isfile("%s.deployed" % path):

                    print('download api program: %s' % _service.id)
                    r = InvokeService('okapi/storage/1/okapi/program/%s' % _id).get()
                    print("download file status: %s" % r.code)
                    if r.code == 200:
                        from tempfile import NamedTemporaryFile
                        import zipfile

                        print(path)
                        try:
                            with NamedTemporaryFile('wb') as f:
                                f.write(r.body if isinstance(r.body, bytes) else eval(r.body))
                                print(f.name)
                                f.flush()
                                z = zipfile.ZipFile(f.name)
                                z.extractall(path)
                                z.close()
                            with open("%s.deployed" % path, 'w'):
                                pass
                            print("extract success")
                        except:
                            dep = {"status": "exited", "message": "{0}.{1}".format(type(r.body), r.body),
                                   "debug": "extract file error, reps:%s" % traceback.format_exc()}
                            InvokeService("okapi/services/1/%s/deploy" % api_id.replace('/', '.'), method='put',
                                          body=dep)
                            sys.exit(7)
                    else:
                        dep = {"status": "exited", "message": r.body, "debug": "download file error, reps:%s" % r}
                        InvokeService("okapi/services/1/%s/deploy" % api_id.replace('/', '.'), method='put', body=dep)
                        sys.exit(7)
                sys.path.insert(0, path)
            except Exception as e:
                dep = {"status": "exited", "message": str(e), "debug": traceback.print_exc()}
                InvokeService("okapi/services/1/%s/deploy" % api_id.replace('/', '.'), method='put', body=dep)
                sys.exit(8)
    print(sys.path)
    print('start serve')
    serve_forever(_service, _port)
    print('main thread exit')
