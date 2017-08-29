from flask import Flask, request
import json

from scripts.ecg_tools import *

app = Flask(__name__)
 
@app.route('/api/ecg/get_signal')
def get_signal():   
    pid = request.args.get('pid', type=int)
    if pid:
        data = ecg_signal(pid)
        return json.dumps(data)
    return 'Bad request: pid is missing. Example: /api/ecg/get_signal?pid=1'
 
@app.route('/api/ecg/get_analysis')
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
