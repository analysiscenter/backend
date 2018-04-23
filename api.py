import numpy as np
from flask import request
from flask_socketio import Namespace
from time import time

from mt_controller import MtController

# init controller objects
mt = MtController()


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

    def _call_controller_method(self, method, event_in, event_out, data, meta):
        print(event_in)
        try:
            payload = method(data, meta)
        except Exception as e:
            print("ERROR", method.__name__, str(e))
            self.emit("ERROR", str(e))
        else:
            print('+'*25 + 'EMIT' + '+'*25)
            print('time', time)
            print('method', method)
            print('in', event_in)
            print('out', event_out)
            if isinstance(data, list):
                print('data', len(data))
            print('meta', meta)
            print('-'*55)
            self.emit(event_out, payload)

    def on_MT_GET_LIST(self, data, meta):
        self._call_controller_method(mt.get_list, "MT GET LIST", "MT_GOT_LIST", data, meta)

    def on_MT_GET_ITEM_DATA(self, data, meta):
        self._call_controller_method(mt.get_item_data, "MT GET ITEM DATA", "MT_GOT_ITEM_DATA", data, meta)

    def on_MT_UPLOAD_IMAGE(self, data, meta):
        self._call_controller_method(mt.upload_image, "MT UPLOAD IMAGE", "MT_GOT_INFERENCE", data, meta)    

    def on_MT_GET_INFERENCE(self, data, meta):
        self._call_controller_method(mt.get_inference, "MT GET INFERENCE", "MT_GOT_INFERENCE", data, meta)