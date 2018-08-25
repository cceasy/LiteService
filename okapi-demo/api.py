# -*- encoding:utf-8 -*-

from flask import Flask, request
import json
import traceback

from pyokapi.client import InvokeService

app = Flask(__name__)

client_id = "okapi.webapi"


@app.route('/', defaults={'path': ''}, methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"])
@app.route('/<path:path>', methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"])
def api_handler(path):
    if len(path.split('/')) < 3:
        return 'No such service', 404
    print(path, request.method)
    print(request.args)
    res = InvokeService(path, method=request.method, args=request.args, headers=request.headers,
                        body=request.get_data()).get()
    if isinstance(res.body, list) or isinstance(res.body, dict):
        res.body = json.dumps(res.body)
    return res.body, res.code, res.headers


@app.context_processor
def utility_processor():
    def urlencode(params):
        import urllib
        return urllib.parse.urlencode(params)

    return dict(urlencode=urlencode)


@app.errorhandler(500)
def internal_server(error):
    return traceback.format_exc(), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0')
