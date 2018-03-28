import os
import sys
import re
import time
from hashlib import sha256

import numpy as np
from watchdog.events import RegexMatchingEventHandler

CURRENT_PATH = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(1, os.path.join(CURRENT_PATH, "ecg"))
from cardio.core.ecg_batch_tools import load_xml_schiller
from cardio.core.utils import get_multiplier


def sha256_checksum(path, block_size=2**16):
    sha = sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(block_size), b""):
            sha.update(block)
    return sha.hexdigest()


def _convert_units(signal, meta, units):
    old_units = meta["units"]
    new_units = [units] * len(old_units)
    multiplier = [get_multiplier(old, new) for old, new in zip(old_units, new_units)]
    multiplier = np.array(multiplier).reshape(-1, 1)
    signal *= multiplier
    meta["units"] = np.asarray(new_units)
    return signal, meta


def _load_signal(path, retries=1, timeout=0.1):
    last_err = None
    for _ in range(retries):
        try:
            signal, meta = load_xml_schiller(path, ["signal", "meta"])
        except Exception as err:
            last_err = err
            time.sleep(timeout)
        else:
            signal, meta = _convert_units(signal, meta, "mV")
            signal = signal.tolist()
            meta["units"] = meta["units"].tolist()
            meta["signame"] = meta["signame"].tolist()
            return signal, meta
    else:
        raise last_err


def _load_data(path, retries=1, timeout=0.1):
    signal, meta = _load_signal(path, retries, timeout)
    sha = sha256_checksum(path)
    signal_data = {
        "file_name": os.path.basename(path),
        "modification_time": os.path.getmtime(path),
        "signal": signal,
        "meta": meta,
        "annotation": [],
    }
    return sha, signal_data


class Handler(RegexMatchingEventHandler):
    def __init__(self, namespace, watch_dir, annotation_path, *args, **kwargs):
        pattern = "^.+\.xml$"
        super().__init__([pattern], *args, **kwargs)
        self.namespace = namespace
        self.watch_dir = watch_dir
        self.annotation_path = annotation_path
        self.data = {}
        print("Initial loading")
        for path in (os.path.join(watch_dir, f) for f in os.listdir(watch_dir) if re.match(pattern, f)):
            self._update_data(path)
        print(len(self.data), [v["file_name"] for k, v in self.data.items()])

    def _update_data(self, path, retries=1, timeout=0.1):
        sha, signal_data = _load_data(path, retries, timeout)
        existing_data = self.data.get(sha)
        if existing_data is None:
            self.data[sha] = signal_data
        elif existing_data["modification_time"] > signal_data["modification_time"]:
            if len(existing_data["annotation"]) > 0:
                signal_data["annotation"] = existing_data["annotation"]
            self.data[sha] = signal_data
            os.remove(os.path.join(self.watch_dir, existing_data["file_name"]))
        else:
            os.remove(path)

    def _dump_annotation(self):
        print("Dump call")
        for sha, signal_data in self.data.items():
            if len(signal_data["annotation"]) > 0:
                print(sha[:5], signal_data["annotation"])

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

    def _set_annotation(self, data, meta):
        sha = data.get("id")
        if sha is None or sha not in self.data:
            raise ValueError("Invalid sha {}".format(sha))
        annotation = data.get("annotation")
        if annotation is None:
            raise ValueError("Empty annotation")
        self.data[sha]["annotation"] = annotation
        self._dump_annotation()

    def on_created(self, event):
        print("File created:", event)
        self._update_data(event.src_path, retries=5)
        print(len(self.data), [signal_data["file_name"] for sha, signal_data in self.data.items()])
        self.namespace.on_ECG_GET_LIST({}, {})

    def on_deleted(self, event):
        print("File deleted:", event)
        src = os.path.basename(event.src_path)
        data = {}
        for sha, signal_data in self.data.items():
            if signal_data["file_name"] != src:
                data[sha] = signal_data
            else:
                need_dump = len(signal_data["annotation"]) > 0
        self.data = data
        if need_dump:
            self._dump_annotation()
        print(len(self.data), [signal_data["file_name"] for sha, signal_data in self.data.items()])
        self.namespace.on_ECG_GET_LIST({}, {})

    def on_moved(self, event):
        # TODO: redirection to on_created or on_deleted if needed
        print("File renamed:", event)
        src = os.path.basename(event.src_path)
        dst = os.path.basename(event.dest_path)
        for sha, signal_data in self.data.items():
            if signal_data["file_name"] == src:
                signal_data["file_name"] = dst
                need_dump = len(signal_data["annotation"]) > 0
        if need_dump:
            self._dump_annotation()
        print(len(self.data), [signal_data["file_name"] for sha, signal_data in self.data.items()])
        self.namespace.on_ECG_GET_LIST({}, {})
