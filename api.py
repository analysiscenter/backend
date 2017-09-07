from flask import request
from flask_socketio import Namespace
import numpy as np


class API_Namespace(Namespace):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        print("Namespace created")

    def on_connect(self):
        print("User connected", request, request.sid)
        pass

    def on_disconnect(self):
        print("User disconnected", request, request.sid)
        pass

    def on_ECG_GET_LIST(self, data, meta):
        print("GET LIST", data, meta)
        ecg_list = [dict(id=id, name='ecg' + str(id)) for id in range(8)]
        payload = dict(event='ECG_GOT_LIST', data=ecg_list, meta=meta)
        self.emit('ECG_GOT_LIST', payload)

    def on_ECG_GET_ITEM_DATA(self, data, meta):
        signal = np.random.normal(0, 1, size=30)
        data['signal'] = signal
        payload = dict(event='ECG_GOT_ITEM_DATA', data=data, meta=meta)
        self.emit('ECG_GOT_ITEM_DATA', payload)

    def on_ECG_GET_INFERENCE(self, data, meta):
        inference = np.random.normal(0, 1, size=30)
        data['inference'] = inference
        payload = dict(event='ECG_GOT_ITEM_DATA', data=data, meta=meta)
        self.emit('ECG_GOT_INFERENCE', payload)
