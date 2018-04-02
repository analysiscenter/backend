import os
import sys
import re
import time
import json
import random
from hashlib import sha256
from collections import OrderedDict

import numpy as np
from watchdog.events import FileSystemEvent, RegexMatchingEventHandler

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
    def __init__(self, namespace, watch_dir, submitted_annotation_path, annotation_list_path, *args, **kwargs):
        self.pattern = "^.+\.xml$"
        super().__init__([self.pattern], *args, **kwargs)
        self.namespace = namespace
        self.watch_dir = watch_dir
        self.submitted_annotation_path = submitted_annotation_path
        self.data = {}
        print("Initial loading")
        with open(annotation_list_path, encoding="utf8") as json_data:
            self.annotation_dict = json.load(json_data, object_pairs_hook=OrderedDict)
        self.annotation_count_dict = OrderedDict()
        for group, annotations in self.annotation_dict.items():
            if not annotations:
                self.annotation_count_dict[group] = 0
            else:
                for annotation in annotations:
                    self.annotation_count_dict[group + "/" + annotation] = 0
        path_gen = (os.path.join(self.watch_dir, f) for f in os.listdir(self.watch_dir)
                    if re.match(self.pattern, f) is not None)
        for path in path_gen:
            self._update_data(path)
        # TODO: load annotation, update data and counts
        print(len(self.data), [signal_data["file_name"] for sha, signal_data in self.data.items()])

    def _update_data(self, path, retries=1, timeout=0.1):
        sha, signal_data = _load_data(path, retries, timeout)
        existing_data = self.data.get(sha)
        if existing_data is None:
            self.data[sha] = signal_data
        elif existing_data["modification_time"] > signal_data["modification_time"]:
            if len(existing_data["annotation"]) > 0:
                signal_data["annotation"] = existing_data["annotation"]
                self._dump_annotation()
            self.data[sha] = signal_data
            os.remove(os.path.join(self.watch_dir, existing_data["file_name"]))
        else:
            os.remove(path)

    def _dump_annotation(self):
        # TODO: dump annotation
        print("Dump call")
        for sha, signal_data in self.data.items():
            if len(signal_data["annotation"]) > 0:
                print(sha[:5], signal_data["annotation"])

    def _get_annotation_list(self, data, meta):
        data = [{"id": group, "annotations": annotations} for group, annotations in self.annotation_dict.items()]
        return dict(data=data, meta=meta)

    def _get_ecg_list(self, data, meta):
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

    def _get_common_annotation_list(self, data, meta):
        N_TOP_DEFAULT = 5
        n_top = data.get("n_top", N_TOP_DEFAULT)
        d = {annotation: count for annotation, count in self.annotation_count_dict.items() if count > 0}
        annotations = sorted(d, key=lambda x: (-d[x], x))[:n_top]
        data["annotations"] = annotations
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
        for old_annotation in self.data[sha]["annotation"]:
            self.annotation_count_dict[old_annotation] -= 1
        self.data[sha]["annotation"] = annotation
        for new_annotation in self.data[sha]["annotation"]:
            self.annotation_count_dict[new_annotation] += 1
        self._dump_annotation()
        self.namespace.on_ECG_GET_COMMON_ANNOTATION_LIST({}, {})

    def on_created(self, event):
        src = os.path.basename(event.src_path)
        print("File created: {}".format(src))
        self._update_data(event.src_path, retries=5)
        print(len(self.data), [signal_data["file_name"] for sha, signal_data in self.data.items()])
        self.namespace.on_ECG_GET_LIST({}, {})

    def on_deleted(self, event):
        src = os.path.basename(event.src_path)
        print("File deleted: {}".format(src))
        need_dump = False
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
        src = os.path.basename(event.src_path)
        src_match = re.match(self.pattern, src) is not None
        dst = os.path.basename(event.dest_path)
        dst_match = re.match(self.pattern, dst) is not None
        if not src_match and dst_match:
            return self.on_created(FileSystemEvent(event.dest_path))
        elif src_match and not dst_match:
            return self.on_deleted(FileSystemEvent(event.src_path))
        print("File renamed: {} -> {}".format(src, dst))
        need_dump = False
        for sha, signal_data in self.data.items():
            if signal_data["file_name"] == src:
                signal_data["file_name"] = dst
                need_dump = len(signal_data["annotation"]) > 0
        if need_dump:
            self._dump_annotation()
        print(len(self.data), [signal_data["file_name"] for sha, signal_data in self.data.items()])
        self.namespace.on_ECG_GET_LIST({}, {})
