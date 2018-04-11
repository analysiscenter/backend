import logging

from flask import request
from flask_socketio import Namespace
from watchdog.observers import Observer

from .handler import EcgDirectoryHandler


class API_Namespace(Namespace):
    def __init__(self, watch_dir, submitted_annotation_path, annotation_list_path, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger("server." + __name__)
        self.handler = EcgDirectoryHandler(self, watch_dir, submitted_annotation_path, annotation_list_path,
                                           ignore_directories=True)
        observer = Observer()
        observer.schedule(self.handler, watch_dir)
        observer.start()
        self.logger.info("Namespace created")

    def on_connect(self):
        self.logger.info("User connected {}".format(request.sid))

    def on_disconnect(self):
        self.logger.info("User disconnected {}".format(request.sid))

    def _safe_call(self, method, data, meta, event_in, event_out=None):
        self.logger.info("Handling event {}. Data: {}. Meta: {}.".format(event_in, data, meta))
        try:
            payload = method(data, meta)
            if event_out is not None:
                self.emit(event_out, payload)
                self.logger.info("Sending response {}. Meta: {}".format(event_out, meta))
        except Exception as error:
            self.emit("ERROR", str(error))
            self.logger.exception(error)

    def on_ECG_GET_ANNOTATION_LIST(self, data, meta):
        self._safe_call(self.handler._get_annotation_list, data, meta, "ECG_GET_ANNOTATION_LIST",
                        "ECG_GOT_ANNOTATION_LIST")

    def on_ECG_GET_COMMON_ANNOTATION_LIST(self, data, meta):
        self._safe_call(self.handler._get_common_annotation_list, data, meta, "ECG_GET_COMMON_ANNOTATION_LIST",
                        "ECG_GOT_COMMON_ANNOTATION_LIST")

    def on_ECG_GET_LIST(self, data, meta):
        self._safe_call(self.handler._get_ecg_list, data, meta, "ECG_GET_LIST", "ECG_GOT_LIST")

    def on_ECG_GET_ITEM_DATA(self, data, meta):
        self._safe_call(self.handler._get_item_data, data, meta, "ECG_GET_ITEM_DATA", "ECG_GOT_ITEM_DATA")

    def on_ECG_SET_ANNOTATION(self, data, meta):
        self._safe_call(self.handler._set_annotation, data, meta, "ECG_SET_ANNOTATION")
