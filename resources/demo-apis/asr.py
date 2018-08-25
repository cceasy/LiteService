# -*- coding:utf-8 -*-

from urllib.parse import urlencode

@get("/")
def semantic():
    query = api.args.get("query")
    body = {"query": query, "domainIds": ','.join(map(str,range(1,36)))}
    body = urlencode(body)
    headers = {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8", "Accept": "application/json, text/javascript, */*; q=0.01"}
    rsp = InvokeService("http://yuyin.baidu.com/nlp/analysisPreview", method = 'post', headers = headers, body = body).get()
    return rsp.body["results"]