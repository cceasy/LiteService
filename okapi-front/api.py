# -*- encoding:utf-8 -*-

from flask import Flask, render_template, redirect, request
import os
import traceback
import json
import requests
import traceback
from easydict import EasyDict
from werkzeug import secure_filename
from flask import send_from_directory
from pyokapi.client import InvokeService

UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', '/data/upload/')
ALLOWED_EXTENSIONS = set(['zip', 'jar'])

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024
DEFAULT_USER = 'cceasy'


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


@app.context_processor
def utility_processor():
    def urlencode(params):
        import urllib
        return urllib.parse.urlencode(params)

    return dict(urlencode=urlencode)


@app.route('/')
def index():
    return redirect('/services')


@app.route('/services')
def front_list():
    resp = InvokeService('okapi/services/1').get()
    if resp.code == 200:
        api_repo = resp.body
        print('resp.body', api_repo)
        return render_template('service_list.html',
                               apis=sorted(api_repo, key=lambda item: (item['author'], item['name'])))
        # return json.dumps(api_repo)
    else:
        return resp.body, resp.code


@app.route('/services/<service_id>')
def front_api_doc(service_id):
    resp = InvokeService('okapi/services/1/%s' % service_id).get()
    if resp.code == 200:
        api = resp.body
        print('resp.body', api)
        return render_template('service_detail.html', api=api)
        # return json.dumps(api)
    else:
        return resp.body, resp.code


@app.route('/services/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'GET':
        return render_template('add_service.html')
    elif request.method == 'POST':
        try:
            _service = {
                'title': request.form['title'],
                'name': request.form['name'],
                'description': request.form['description'],
                'module_name': request.form['module_name'],
                'version': {
                    '%s' % request.form['version']: {
                        'version': request.form['version'],
                        'runtime': request.form['runtime'],
                        'module_name': request.form['module_name'],
                    }
                },
                'runtime': request.form['runtime'],
                'category': request.form['category'],
                'author': DEFAULT_USER
            }
            # TODO
            file = request.files['file']
            if file and allowed_file(file.filename):
                # filename = secure_filename(file.filename)
                filename = '{0}_{1}_{2}'.format(_service['author'], _service['name'], request.form['version'])
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                with open(file_path, 'rb') as f:
                    file_bytes = f.read()
                _service_id = filename.replace('_', '.')
                r = InvokeService('okapi/storage/1/okapi/program/{0}'.format(_service_id), method='post',
                                  body=file_bytes).get()
                if r.code != 201 and r.code != 200:
                    return 'transfer upload file error', 500
                r = InvokeService('okapi/services/1', method='post', body=_service).get()
                if r.code != 201 and r.code != 200:
                    return 'add service error', 500
                r = InvokeService('okapi/services/1/{0}/deploy'.format(_service_id), method='post').get()
                if r.code != 201 and r.code != 200:
                    return 'Add service success. Deploy failed.\n {0}'.format(r.body)
                return 'Deploy service success', 201
        except:
            return traceback.format_exc()
        return 'upload form data error'


@app.route('/services/upload/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.errorhandler(500)
def internal_server():
    return traceback.format_exc()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
