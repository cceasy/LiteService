#!/usr/bin/env python

# -*- coding:utf-8 -*-

import os
os.chdir(os.path.dirname(__file__))

from api import app 
import flup.server.fcgi

if __name__ == '__main__':
    flup.server.fcgi.WSGIServer(app).run()
