import traceback

from flask import request
from flask_socketio import Namespace
from watchdog.observers import Observer

from .handler import Handler


class API_Namespace(Namespace):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        watch_dir = "D:\\Projects\\GitHub\\backend\\annotation\\watch\\"
        self.handler = Handler(self, watch_dir, ignore_directories=True)
        self.data = self.handler.data
        self.observer = Observer()
        self.observer.schedule(self.handler, watch_dir)
        self.observer.start()
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

    def _get_list(self, data, meta):
        data = []
        for sha in self.data:
            signal_data = {
                "id": sha,
                "timestamp": self.data[sha]["meta"]["timestamp"],
                "is_annotated": len(self.data[sha]["annotation"]) > 0,
            }
            data.append(signal_data)
        data = sorted(data, key=lambda val: val["timestamp"], reverse=True)
        for d in data:
            d["timestamp"] = d["timestamp"].strftime("%d.%m.%Y %H:%M:%S")
        return dict(data=data, meta=meta)

    def on_ECG_GET_LIST(self, data, meta):
        self._safe_call(self._get_list, data, meta, "ECG_GET_LIST", "ECG_GOT_LIST")

    def _get_item_data(self, data, meta):
        sha = data.get("id")
        if sha is None or sha not in self.data:
            raise ValueError("Invalid sha {}".format(sha))
        data["signal"] = self.data[sha]["signal"]
        data["frequency"] = self.data[sha]["meta"]["fs"]
        data["units"] = self.data[sha]["meta"]["units"]
        data["signame"] = self.data[sha]["meta"]["signame"]
        data["annotation"] = self.data[sha]["annotation"]
        return dict(data=data, meta=meta)

    def on_ECG_GET_ITEM_DATA(self, data, meta):
        self._safe_call(self._get_item_data, data, meta, "ECG_GET_ITEM_DATA", "ECG_GOT_ITEM_DATA")

    def _set_annotation(self, data, meta):
        sha = data.get("id")
        if sha is None or sha not in self.data:
            raise ValueError("Invalid sha {}".format(sha))
        annotation = data.get("annotation")
        if annotation is None:
            raise ValueError("Empty annotation")
        self.data[sha]["annotation"] = annotation

    def on_ECG_SET_ANNOTATION(self, data, meta):
        self._safe_call(self._set_annotation, data, meta, "ECG_SET_ANNOTATION")
