# -*- coding:utf-8 -*-
import json

@get("/")
def tuling():
    query = api.args.get("query")
    rsp = InvokeService("http://www.tuling123.com/openapi/api",  args = {"key": "1f59a42473dc3a4ccc69023088ec8a52", "info": query}).get()
    rsp.body = json.loads(rsp.body.decode())
    return {'result': rsp.body["text"]}