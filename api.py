import numpy as np
from flask import request
from flask_socketio import Namespace

from ecg_controller import EcgController
from ct_controller import CtController

# init controller objects
ecg = EcgController()
ct = CtController()


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
        print(event_in, data, meta)
        try:
            payload = method(data, meta)
        except Exception as e:
            print("ERROR", method.__name__, data, meta)
            self.emit("ERROR", str(e))
        else:
            self.emit(event_out, payload)

    def on_ECG_GET_LIST(self, data, meta):
        self._call_controller_method(ecg.get_list, "ECG GET LIST", "ECG_GOT_LIST", data, meta)

    def on_ECG_GET_ITEM_DATA(self, data, meta):
        self._call_controller_method(ecg.get_item_data, "ECG GET ITEM DATA", "ECG_GOT_ITEM_DATA", data, meta)

    def on_ECG_GET_INFERENCE(self, data, meta):
        self._call_controller_method(ecg.get_inference, "ECG GET INFERENCE", "ECG_GOT_INFERENCE", data, meta)

    def on_CT_GET_LIST(self, data, meta):
        self._call_controller_method(ct.get_list, "CT GET LIST", "CT_GOT_LIST", data, meta)

    def on_CT_GET_ITEM_DATA(self, data, meta):
        self._call_controller_method(ct.get_item_data, "CT GET ITEM DATA", "CT_GOT_ITEM_DATA", data, meta)

    def on_CT_GET_INFERENCE(self, data, meta):
        self._call_controller_method(ct.get_inference, "CT GET INFERENCE", "CT_GOT_INFERENCE", data, meta)
