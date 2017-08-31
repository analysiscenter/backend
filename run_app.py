import json
from flask import Flask, request, make_response, current_app
from datetime import timedelta
from functools import update_wrapper

from scripts.ecg_tools import *

app = Flask(__name__)

def crossdomain(origin=None, methods=None, headers=None,
                max_age=21600, attach_to_all=True,
                automatic_options=True):
    if methods is not None:
        methods = ', '.join(sorted(x.upper() for x in methods))
    if headers is not None and not isinstance(headers, basestring):
        headers = ', '.join(x.upper() for x in headers)
    if not isinstance(origin, basestring):
        origin = ', '.join(origin)
    if isinstance(max_age, timedelta):
        max_age = max_age.total_seconds()

    def get_methods():
        if methods is not None:
            return methods

        options_resp = current_app.make_default_options_response()
        return options_resp.headers['allow']

    def decorator(f):
        def wrapped_function(*args, **kwargs):
            if automatic_options and request.method == 'OPTIONS':
                resp = current_app.make_default_options_response()
            else:
                resp = make_response(f(*args, **kwargs))
            if not attach_to_all and request.method != 'OPTIONS':
                return resp

            h = resp.headers

            h['Access-Control-Allow-Origin'] = origin
            h['Access-Control-Allow-Methods'] = get_methods()
            h['Access-Control-Max-Age'] = str(max_age)
            if headers is not None:
                h['Access-Control-Allow-Headers'] = headers
            return resp

        f.provide_automatic_options = False
        return update_wrapper(wrapped_function, f)
    return decorator
 
@app.route('/api/ecg/get_signal')
@crossdomain(origin='*')
def get_signal():   
    pid = request.args.get('pid', type=int)
    if pid:
        data = ecg_signal(pid)
        return json.dumps(data)
    return 'Bad request: pid is missing. Example: /api/ecg/get_signal?pid=1'
 
@app.route('/api/ecg/get_analysis')
@crossdomain(origin='*')
def get_results():   
    pid = request.args.get('pid', type=int)
    if pid:
        data = analysis_results(pid)
        return json.dumps(data)
    return 'Bad request: pid is missing. Example: /api/ecg/get_results?pid=1'

@app.route('/')
def index():
    return 'API server is ready. Sample request: /api/ecg/get_signal?pid=1'
    
if __name__ == '__main__':
    app.run(debug=True)
