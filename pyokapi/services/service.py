import pymongo
import random
from pyokapi import *
import threading
import time

_conn = pymongo.Connection(MONGO_HOST, MONGO_PORT)
_apis = _conn.okapi.service
_deploy = _conn.okapi.deploys
_docs = _conn.okapi.doc

dkrt = "http://172.17.0.1:2375"


def get_all_containers():
    return InvokeService(dkrt + '/containers/json?all=1&filters={"status":["running"]}').get()


def create_container(author, runtime):
    name = "%s.%s" % (author, runtime)
    if runtime == "python":
        image = "ls/okapi-py2"
    elif runtime == "python3":
        image = "ls/okapi-py3"
    elif runtime == "java":
        image = "ls/okapi-java"
    else:
        raise Exception("not supported runtime: %s" % runtime)
    d = {"Hostname": name, "Image": image, "Cmd": ['/bin/sleep', '365d'], "Entrypoint": "",
         "HostConfig": {"Env": ["CONTAINER=%s" % name], "NetworkMode": "docker_default"},
         "NetworkingConfig": {"EndpointsConfig": {"docker_default": {"Links": ["docker_okapiserver_1:okapi"]}}}}
    print('deploy config: %s' % d)
    resp = InvokeService(dkrt + "/containers/create", args={'name': name}, method='post', body=d).get()
    if resp.code == 201:
        print('create %s success' % name)
        resp = InvokeService(dkrt + '/containers/%s/start' % name, method='post').get()
        if resp.code == 204:
            print("start container %s success" % name)
        else:
            print("start container %s fails: %s" % (name, resp))
    else:
        print('create %s fails, resp: %s' % (name, resp))


recreated = set()


def start_container(author, runtime, restart=False, recreate=False):
    name = "%s.%s" % (author, runtime)
    resp = InvokeService(dkrt + '/containers/%s/json' % name).get()
    if resp.code == 200:
        if recreate and name not in recreated:
            recreated.add(name)
            resp = InvokeService(dkrt + "/containers/%s" % name, args={"force": True}, method="delete").get()
            if resp.code == 204:
                print("success delete container %s" % name)
                create_container(author, runtime)
            else:
                print("fails to delte container %s:%s" % (name, resp))
        elif resp.body["State"]["Running"]:
            if restart and name not in recreated:
                recreated.add(name)
                resp = InvokeService(dkrt + '/containers/%s/restart' % name, method="post").get()
                if resp.code == 204:
                    print("restart container %s success" % name)
                else:
                    print("restart container %s fails: %s" % (name, resp))
            else:
                print("container %s already started" % name)

        else:
            resp = InvokeService(dkrt + '/containers/%s/start' % name, method="post").get()
            if resp.code == 204:
                print("start container %s success" % name)
            else:
                print("start container %s fails: %s" % (name, resp))
    elif resp.code == 404:
        create_container(author, runtime)


def start_service(_api, restart=False, recreate=False):
    print('# start service: ', _api)
    _id = "%s/%s/%s" % (_api["author"], _api["name"], _api["version"])
    if _id == "okapi/storage/1":
        return
    _dep = edict(_deploy.find_one({"service_id": _id}))
    if not _dep:
        _dep = edict({"service_id": _id, "deploys": []})
        _deploy.insert(_dep)
    _dep["deploys"] = []

    # start_container(_api.author, _api.runtime, restart=restart, recreate=True)
    start_container(_api.author, _api.runtime, restart=restart, recreate=recreate)

    port = random.randint(12141, 65530)
    if _api.runtime == "python":
        cmd = ["python", "-m", "pyokapi.server", _id, str(port)]
    elif _api.runtime == "python3":
        cmd = ["python3", "-m", "pyokapi.server", _id, str(port)]
    elif _api.runtime == "java":
        cmd = ["java", "-jar", "okapiserver.jar", _id, str(port)]
    else:
        print("unsupported runtime %s for service %s" % (_api.runtime, name), 500)
    d = {"AttachStdin": False, "AttachStdout": False, "AttachStderr": False, "Tty": False, "Cmd": cmd}
    print('deploy config: %s' % d)
    resp = InvokeService(dkrt + "/containers/%s.%s/exec" % (_api.author, _api.runtime), method='post', body=d).get()

    if resp.code == 201:
        ctn_id = resp.body.Id
        resp = InvokeService(dkrt + "/exec/%s/start" % ctn_id, method='post',
                             body={"Detach": True, "Tty": False, }).get()
        print(resp)
        if resp.code == 200:
            resp = InvokeService(dkrt + "/exec/%s/json" % ctn_id).get()
            if resp.code == 200 and resp.body["Running"]:
                resp = InvokeService(dkrt + "/containers/%s/json" % resp.body["ContainerID"]).get()
                # print('get container json:', resp)
                if resp.code == 200:
                    ctn = resp.body
                    # print("exec details:%s" % resp.body)
                    # _dep["deploys"].append({"name": ctn_id, "status": "deploying", "host": ctn["NetworkSettings"]["IPAddress"], "port": port})
                    _dep["deploys"].append({"name": ctn_id, "status": "running",
                                            "host": ctn["NetworkSettings"]["Networks"]["docker_default"]["IPAddress"],
                                            "port": port})
                    _deploy.save(_dep)
                    return 'success'
                else:
                    print("error somehow")
                    return 'error somehow'
            else:
                print('get exec info fails:%s' % resp, 503)
                return 'get exec info fails:%s' % resp
        else:
            print('start instance %s error, reason: %s' % (ctn_id, resp), 500)
            return 'start instance %s error, reason: %s' % (ctn_id, resp)
    else:
        print('create docker service exec fails, reason: %s' % resp, 500)
        return 'create docker service exec fails, reason: %s' % resp


def init():
    time.sleep(10)
    print('threading started')

    _deps = _apis.find()
    for _api in _deps:
        _api = edict(_api)
        # print(_api)
        _vers = _api["version"]
        for _ver in _vers:
            _api.update(_vers[_ver])
            _api["version"] = _ver
            _api = edict(_api)
            # print(_api)
            start_service(_api, restart=False)


threading.Thread(target=init).start()


@get("/")
def s_list():
    _api = _apis.find(api.args,
                      {"_id": 0, "name": 1, "author": 1, "version": 1, "title": 1, "description": 1, "category": 1})
    _all = []
    for _ in _api:
        _vers = _["version"].keys()
        if len(_vers) <= 0:
            max_ver = '0'
        else:
            max_ver = str(max([int(x) for x in _vers]))
            _.update(_["version"][max_ver])
        _["version"] = max_ver
        _["id"] = "/".join([_["author"], _["name"], _["version"]])
        _["id2"] = ".".join([_["author"], _["name"], _["version"]])
        _all.append(_)
    return _all


@post("/")
def s_add():
    s = api.body
    if not isinstance(s, dict):
        return 'input data must be json with Content-Type header application/json', 502
    key = s.keys()
    if set(key) < set(['name', 'author', 'title', 'description', 'category']):
        return 'fields error', 504
    _api = _apis.find_one({"author": s.author, "name": s.name})
    if not _api:
        # s["version"] = {}
        s["create_time"] = time.time()
        s["update_time"] = s["create_time"]
        _apis.insert(s)
        return 'success', 201
    else:
        msg = 'the same name of your service exists, you may specify another name'
        return msg, 400


def find_service_by_id(_id):
    try:
        seg = _id.split('.')
        author, name, version = seg
        _api = _apis.find_one({"author": author, "name": name}, {"_id": 0})

        if version == 'latest':
            _vers = _api["version"].keys()
            if len(_vers) == 0:
                version = '0'
            else:
                version = str(max([int(x) for x in _vers]))

        if version in _api["version"]:
            _api.update(_api["version"][version])
            _api["version"] = version
        else:
            _api["version"] = '0'

        _api["id"] = "/".join((_api["author"], _api["name"], _api["version"]))
        _api["id2"] = ".".join((_api["author"], _api["name"], _api["version"]))
        return edict(_api)
    except:
        pass


@get("/<id>")
def s_detail(id):
    _api = find_service_by_id(id)
    if _api:
        _id = _api["id"]
        _deps = _deploy.find_one({"service_id": _id})
        if not _deps or not _deps["deploys"]:
            _api["deploy"] = {"status": "notdeploy", "message": "service program not uploaded", "debug": ""}
        else:
            _dep = _deps["deploys"][0]
            _dep.setdefault("status", "notdeploy")
            _dep.setdefault("message", "")
            _dep.setdefault("debug", "")
            _api["deploy"] = {"status": _dep["status"], "message": _dep["message"], "debug": _dep["debug"]}
        return _api
    return 'no such service: %s' % id, 404


@put("/<id>")
def modify_info(id):
    author, name, version = id.split('.')
    _api = _apis.find_one({"author": author, "name": name})
    key = api.body.keys()
    if key > set(['title', 'description', 'category']):
        return 'unkonw key occurs', 405
    _api.update(api.body)
    _apis.save(_api)
    return 'service info updated success'


@get("/<id>/update")
def get_updates(id):
    author, name, version = id.split(".")
    _api = _apis.find_one({"author": author, "name": name})
    if not _api:
        return "no such service %s" % id, 404

    vers = []
    for _ver, _val in _api["version"].items():
        _val["version"] = _ver
        vers.append(_val)
    vers = sorted(vers, key=lambda x: x["time"], reverse=True)
    return vers


@post("/<id>/update")
def create_update(id):
    author, name, version = id.split(".")
    _api = _apis.find_one({"author": author, "name": name})
    if not _api:
        return "no such service %s" % id, 404
    elif version in _api["version"]:
        return "the service has the version number %s" % version, 503
    elif api.body.keys() < set(["runtime", "module_name", "message"]):
        return "missing some fields", 502
    else:
        api.body["time"] = time.time()
        _api["version"][version] = api.body
        _apis.save(_api)
        _api.update(api.body)
        _api["version"] = version
        start_service(edict(_api))


@get("/<id>/version")
def get_versions(id):
    author, name, version = id.split('.')
    _svcs = _apis.find_one({"author": author, "name": name})
    _vers = sorted(_svcs["version"].keys(), key=lambda x: int(x), reverse=True)
    return _vers


@post("/<id>/api")
def add_apis(id):
    author, name, version = id.split('.')
    svc = _apis.find_one({"author": author, "name": name})
    if svc:
        svc["version"][version]["api"] = api.body
        _apis.save(svc)
    return "no such service: %s" % id, 404


@get("/<id>/api")
def get_apis(id):
    svc = find_service_by_id(id)
    if svc:
        if 'api' in svc:
            return svc.api
        else:
            return []
    return "no such service: %s" % id, 404


@get("/<id>/api/<api_id>")
def api_detail(id, api_id):
    svc = find_service_by_id(id)
    _api = None
    if svc:
        for a in svc["api"]:
            if a["function"] == api_id:
                _api = a
                break
        if _api:
            id = '.'.join(id.split('.')[0:2])
            doc = _docs.find_one({"id": "%s.%s" % (id, api_id)}, {"_id": 0})
            if doc:
                _api.update(doc)
            return _api
        else:
            return 'service has no such an api: %s' % api_id
    else:
        return 'no such service: %s' % id, 404


@put("/<id>/api/<api_id>")
def api_doc(id, api_id):
    svc = find_service_by_id(id)
    _api = None
    if svc:
        for a in svc["api"]:
            if a["function"] == api_id:
                _api = a
                break
        if _api:
            id = '.'.join(id.split('.')[0:2])
            doc = _docs.find_one({"id": "%s.%s" % (id, api_id)})
            if not doc:
                doc = {"id": "%s.%s" % (id, api_id)}
            doc.update(api.body)
            _docs.save(doc)
            return
        else:
            return 'service has no such an api: %s' % api_id
    else:
        return 'no such service: %s' % id, 404


@get("/<id>/deploy")
def s_dep_list(id):
    _api = find_service_by_id(id)
    if not _api:
        return 'no such service: %s' % id, 404

    _id = _api["id"]
    _deps = _deploy.find_one({"service_id": _id})
    if not _deps:
        return 'service not deployed yet: %s' % _id, 405
    del _deps["_id"]
    return _deps


@get("/<id>/deploy/select")
def s_dep_select(id):
    _api = find_service_by_id(id)
    if not _api:
        return 'no such service: %s' % id, 404

    _id = _api["id"]
    _deps = _deploy.find_one({"service_id": _id})
    if not _deps:
        return 'service not deployed yet: %s' % _id, 405
    cand = [x for x in _deps["deploys"] if x["status"] == "running"]
    if len(cand) == 0:
        return "there's no avaivable running instance", 406
    _dep = random.choice(cand)
    _dep["service_id"] = _deps["service_id"]
    del _dep['status']
    return _dep


@post("/<id>/deploy")
def s_dep(id):
    _api = find_service_by_id(id)
    if not _api:
        return 'no such service: %s' % id, 404

    _id = _api["id"]
    _deps = edict(_deploy.find_one({"service_id": _id}))
    if not _deps:
        _deps = edict({"service_id": _id, "deploys": []})
        _deploy.insert(_deps)
    else:
        print("already deployed, will overwrite")

    r = start_service(_api)
    if r == 'success':
        return r, 201
    return r


@put("/<id>/deploy")
def m_dep(id):
    _api = find_service_by_id(id)
    if not _api:
        return 'no such service: %s' % id, 404

    _id = _api["id"]
    _deps = edict(_deploy.find_one({"service_id": _id}))
    if not _deps or len(_deps.deploys) == 0:
        return 'service not deployed: %s' % id, 500
    else:
        # print('type:%s, %s' % (type(api.body), api.body))
        _deps.deploys[0].update(api.body)
        _deploy.save(_deps)


@put("/<id>/deploy/<inst>")
def add_dep(id, inst):
    _api = find_service_by_id(id)
    if not _api:
        return 'no such service: %s' % id, 404

    _id = _api["id"]
    _deps = _deploy.find_one({"service_id": _id})

    if not _deps:
        # return 'service (%s) not deployed in instance (%s)' % (id, inst), 405
        _deps = edict({"service_id": _id, "deploys": []})
        _deploy.insert(_deps)

    _deps["deploys"] = []
    try:
        res = next(filter(lambda x: x["name"] == inst, _deps["deploys"]))
    except StopIteration:
        res = {"name": inst}
        _deps["deploys"].append(res)
    resp = InvokeService(dkrt + "/containers/%s/json" % inst).get()
    if resp.code == 200:
        # res["host"] = resp.body["NetworkSettings"]["IPAddress"]
        res["host"] = resp.body["NetworkSettings"]["Networks"]["docker_default"]["IPAddress"]
        res["message"] = "add by ljh as a test message!"
        res["port"] = int(api.args.port)
        res["status"] = "running"
        result = ("put deploy success %s" % inst, 200)
    else:
        res["status"] = "stopped"
        result = "instance %s not started" % inst, 403
    _deploy.save(_deps)
    return result


@delete("/<id>/deploy/<inst>")
def s_stop(id, inst):
    _api = find_service_by_id(id)
    if not _api:
        return 'no such service: %s' % id, 404

    _id = _api["id"]
    _deps = _deploy.find_one({"service_id": _id, "deploys": {"$elemMatch": {"name": inst}}})

    if not _deps:
        return 'service (%s) not deployed in instance (%s)' % (id, inst), 405

    res = next(filter(lambda x: x["name"] == inst, _deps["deploys"]))
    res["status"] = "stopped"
    del res["host"]
    del res["port"]

    _deploy.save(_deps)
