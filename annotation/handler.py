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
            return signal.tolist(), meta
    else:
        raise last_err


def _load_data(path, retries=1, timeout=0.1):
    signal, meta = _load_signal(path, retries, timeout)
    sha = sha256_checksum(path)
    data = {
        "file_name": os.path.basename(path),
        "modification_time": os.path.getmtime(path),
        "signal": signal,
        "meta": meta,
        "annotation": {},
    }
    return sha, data


class Handler(RegexMatchingEventHandler):
    def __init__(self, namespace, watch_dir, *args, **kwargs):
        pattern = "^.+\.xml$"
        super().__init__([pattern], *args, **kwargs)
        self.namespace = namespace
        self.watch_dir = watch_dir
        self.data = {}
        print("Initial loading")
        for path in (os.path.join(watch_dir, f) for f in os.listdir(watch_dir) if re.match(pattern, f)):
            self._update_data(path)
        print(len(self.data), [v["file_name"] for k, v in self.data.items()])

    def _update_data(self, path, retries=1, timeout=0.1):
        sha, data = _load_data(path, retries, timeout)
        existing_data = self.data.get(sha)
        if existing_data is None:
            self.data[sha] = data
        elif existing_data["modification_time"] < data["modification_time"]:
            # TODO: check if annotation exists
            self.data[sha] = data
            os.remove(os.path.join(self.watch_dir, existing_data["file_name"]))
        else:
            os.remove(path)

    def on_created(self, event):
        print("File created:", event)
        self._update_data(event.src_path, retries=5)
        print(len(self.data), [v["file_name"] for k, v in self.data.items()])
        self.namespace.on_ECG_GET_LIST({}, {})

    def on_deleted(self, event):
        print("File deleted:", event)
        src = os.path.basename(event.src_path)
        self.data = {k: v for k, v in self.data.items() if v["file_name"] != src}
        print(len(self.data), [v["file_name"] for k, v in self.data.items()])
        self.namespace.on_ECG_GET_LIST({}, {})

    def on_moved(self, event):
        # TODO: redirection to on_created or on_deleted if needed
        print("File renamed:", event)
        src = os.path.basename(event.src_path)
        dst = os.path.basename(event.dest_path)
        for k, v in self.data.items():
            if v["file_name"] == src:
                v["file_name"] = dst
        print(len(self.data), [v["file_name"] for k, v in self.data.items()])
        self.namespace.on_ECG_GET_LIST({}, {})
