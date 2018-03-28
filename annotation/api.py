import traceback

from flask import request
from flask_socketio import Namespace
from watchdog.observers import Observer

from .handler import Handler


class API_Namespace(Namespace):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        watch_dir = "D:\\Projects\\GitHub\\backend\\annotation\\watch\\"
        annotation_path = ""
        self.handler = Handler(self, watch_dir, annotation_path, ignore_directories=True)
        observer = Observer()
        observer.schedule(self.handler, watch_dir)
        observer.start()
        print("Namespace created")

    def on_connect(self):
        print("User connected", request, request.sid)

    def on_disconnect(self):
        print("User disconnected", request, request.sid)

    def _safe_call(self, method, data, meta, event_in, event_out=None):
        print(event_in, data, meta)
        try:
            payload = method(data, meta)
            if event_out is not None:
                self.emit(event_out, payload)
        except Exception as error:
            print("ERROR " + event_in, data, meta)
            traceback.print_exc()
            self.emit("ERROR", str(error))

    def on_ECG_GET_LIST(self, data, meta):
        self._safe_call(self.handler._get_list, data, meta, "ECG_GET_LIST", "ECG_GOT_LIST")

    def on_ECG_GET_ITEM_DATA(self, data, meta):
        self._safe_call(self.handler._get_item_data, data, meta, "ECG_GET_ITEM_DATA", "ECG_GOT_ITEM_DATA")

    def on_ECG_SET_ANNOTATION(self, data, meta):
        self._safe_call(self.handler._set_annotation, data, meta, "ECG_SET_ANNOTATION")
