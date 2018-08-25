# -*- encoding:utf-8 -*-
# id: my.localservices.v1

@get("/adder")
def get():
    a = api.args.get('x')
    b = api.args.get('b')
    return a + b
