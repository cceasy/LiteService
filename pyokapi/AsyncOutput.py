# -*- coding:utf-8 -*-

from tornado.httpclient import AsyncHTTPClient
from tornado import ioloop, gen
import time
import threading
import logging
import traceback

logging.getLogger().setLevel(logging.ERROR)


class AsyncOutput():
    _Init = False

    @classmethod
    def Init(cls):
        threading.Thread(target=cls._start_ioloop).start()

        # cls._start_ioloop()

    @classmethod
    def _start_ioloop(cls):
        print("%s, ==, %s" % (ioloop.IOLoop.current(), threading.current_thread()))
        try:
            ioloop.IOLoop.current().start()
        except:
            print('ioloop already running')

    def __init__(self, future, id):
        if not AsyncOutput._Init:
            AsyncOutput.Init()
            AsyncOutput._Init = True
        self.id = id
        self.resp = None
        self.ioloop = ioloop.IOLoop()
        self.future = future
        ioloop.IOLoop.current().add_future(future, self._callback)

    def _callback(self, future):
        print('callback, id: %s, ioloop: %s, threading: %s' % (self.id, self.ioloop, threading.current_thread()))
        try:
            self.resp = future.result()
        except:
            traceback.print_exc()
        self.ioloop.stop()

    def get(self):
        print('ioloop create %s, %s' % (self.id, self.ioloop))
        self.ioloop.start()
        print('result got, id: %s, ioloop: %s, threading: %s' % (self.id, self.ioloop, threading.current_thread()))
        return self.resp


if __name__ == '__main__':

    def test():
        client = AsyncHTTPClient()

        r = []

        for i in range(10):
            print('start i: %s' % i)
            func = client.fetch('http://www.baidu.com')
            ao = AsyncOutput(func, i)
            r.append(ao)

        for i in range(10):
            print("result %s: %s" % (i, r[i].get().code))
        print('continue')


    def _c():
        print('1234')


    # ioloop.IOLoop.current().add_timeout(time.time() + .1, lambda:None)
    test()
    # threading.Thread(target = test).start()
    # ioloop.IOLoop.current().start()


# ioloop.IOLoop.current().start()
