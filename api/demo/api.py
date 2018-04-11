import logging

from flask import request
from flask_socketio import Namespace

from .ecg_controller import EcgController
from .ct_controller import CtController

# init controller objects
ecg = EcgController()
ct = CtController()


class API_Namespace(Namespace):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger("server." + __name__)

    def on_connect(self):
        self.logger.info("User connected {}".format(request.sid))

    def on_disconnect(self):
        self.logger.info("User disconnected {}".format(request.sid))

    def _call_controller_method(self, method, event_in, event_out, data, meta):
        self.logger.info("Handling event {}. Data: {}. Meta: {}.".format(event_in, data, meta))
        try:
            payload = method(data, meta)
        except Exception as error:
            self.emit("ERROR", str(error))
            self.logger.exception(error)
        else:
            self.emit(event_out, payload)
            self.logger.info("Sending response {}. Meta: {}".format(event_out, meta))

    def on_ECG_GET_LIST(self, data, meta):
        self._call_controller_method(ecg.get_list, "ECG_GET_LIST", "ECG_GOT_LIST", data, meta)

    def on_ECG_GET_ITEM_DATA(self, data, meta):
        self._call_controller_method(ecg.get_item_data, "ECG_GET_ITEM_DATA", "ECG_GOT_ITEM_DATA", data, meta)

    def on_ECG_GET_INFERENCE(self, data, meta):
        self._call_controller_method(ecg.get_inference, "ECG_GET_INFERENCE", "ECG_GOT_INFERENCE", data, meta)

    def on_CT_GET_LIST(self, data, meta):
        self._call_controller_method(ct.get_list, "CT_GET_LIST", "CT_GOT_LIST", data, meta)

    def on_CT_GET_ITEM_DATA(self, data, meta):
        self._call_controller_method(ct.get_item_data, "CT_GET_ITEM_DATA", "CT_GOT_ITEM_DATA", data, meta)

    def on_CT_GET_INFERENCE(self, data, meta):
        self._call_controller_method(ct.get_inference, "CT_GET_INFERENCE", "CT_GOT_INFERENCE", data, meta)
