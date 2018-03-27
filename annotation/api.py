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

    def on_ECG_GET_LIST(self, data, meta):
        print("ECG_GET_LIST", data, meta)
        try:
            data = []
            for sha in self.data:
                signal_data = {
                    "id": sha,
                    "timestamp": self.data[sha]["meta"]["timestamp"],
                    "is_annotated": len(self.data[sha]["annotation"]),
                }
                data.append(signal_data)
            data = sorted(data, key=lambda val: val["timestamp"], reverse=True)
            for d in data:
                d["timestamp"] = d["timestamp"].strftime("%d.%m.%Y %H:%M:%S")
            payload = dict(data=data, meta=meta)
        except Exception as e:
            print("ERROR ECG_GET_LIST", data, meta)
            self.emit("ERROR", str(e))
        else:
            self.emit("ECG_GOT_LIST", payload)

    def on_ECG_GET_ITEM_DATA(self, data, meta):
        print("ECG_GET_ITEM_DATA", data, meta)
        try:
            sha = data.get("id")
            if sha is None or sha not in self.data:
                raise ValueError("Invalid sha")
            data["signal"] = self.data[sha]["signal"]
            data["frequency"] = self.data[sha]["meta"]["fs"]
            data["units"] = self.data[sha]["meta"]["units"]
            data["signame"] = self.data[sha]["meta"]["signame"]
            data["annotation"] = self.data[sha]["annotation"]
            payload = dict(data=data, meta=meta)
        except Exception as e:
            print("ERROR ECG_GET_ITEM_DATA", data, meta)
            self.emit("ERROR", str(e))
        else:
            self.emit("ECG_GOT_ITEM_DATA", payload)
