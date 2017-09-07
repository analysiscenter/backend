from flask_socketio import Namespace
import numpy as np


class API_Namespace(Namespace):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        print("Namespace created")

    def on_connect(self):
        pass

    def on_disconnect(self):
        pass

    def on_ECG_GET_LIST(self, data, meta):
        ecg_list = [dict(id=id, name='ecg'+str(id)) for id in range(8)]
        self.emit('ECG_GOT_LIST', ecg_list, meta)

    def on_ECG_GET_ITEM_DATA(self, data, meta):
        signal = np.random.normal(0, 1, size=30)
        data['signal'] = signal
        self.emit('ECG_GOT_ITEM_DATA', data, meta)

    def on_ECG_GET_INFERENCE(self, data, meta):
        inference = np.random.normal(0, 1, size=30)
        data['inference'] = inference
        self.emit('ECG_GOT_INFERENCE', data, meta)
