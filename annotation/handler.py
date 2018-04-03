import os
import re
import json
from collections import OrderedDict

import numpy as np
import pandas as pd
from watchdog.events import FileSystemEvent, RegexMatchingEventHandler

from .loader import load_data


class Handler(RegexMatchingEventHandler):
    def __init__(self, namespace, watch_dir, submitted_annotation_path, annotation_list_path, *args, **kwargs):
        self.pattern = "^.+\.xml$"
        super().__init__([self.pattern], *args, **kwargs)
        self.namespace = namespace
        self.watch_dir = watch_dir
        self.submitted_annotation_path = submitted_annotation_path
        self.annotation_list_path = annotation_list_path
        self.data = OrderedDict()

        print("Initial loading")
        self._load_annotation_list()
        self._load_data()
        self._load_submitted_annotation()
        print(len(self.data), [signal_data["file_name"] for sha, signal_data in self.data.items()])

    def _load_annotation_list(self):
        with open(self.annotation_list_path, encoding="utf-8") as json_data:
            self.annotation_dict = json.load(json_data, object_pairs_hook=OrderedDict)
        self.annotation_count_dict = OrderedDict()
        for group, annotations in self.annotation_dict.items():
            if not annotations:
                self.annotation_count_dict[group] = 0
            else:
                for annotation in annotations:
                    self.annotation_count_dict[group + "/" + annotation] = 0

    def _load_data(self):
        path_gen = (os.path.join(self.watch_dir, f) for f in sorted(os.listdir(self.watch_dir))
                    if re.match(self.pattern, f) is not None)
        for path in path_gen:
            self._update_data(path)

    def _load_submitted_annotation(self):
        if not os.path.isfile(self.submitted_annotation_path):
            return
        df = pd.read_feather(self.submitted_annotation_path).set_index("index")
        counts = df.sum()
        for annotation in self.annotation_count_dict:
            self.annotation_count_dict[annotation] = counts.get(annotation, 0)
        for sha, signal_data in self.data.items():
            if signal_data["file_name"] in df.index:
                annotation = df.loc[signal_data["file_name"]]
                signal_data["annotation"] = annotation[annotation != 0].index.tolist()

    def _update_data(self, path, retries=1, timeout=0.1):
        sha, signal_data = load_data(path, retries, timeout)
        existing_data = self.data.get(sha)
        if existing_data is None:
            self.data[sha] = signal_data
        elif existing_data["modification_time"] > signal_data["modification_time"]:
            if existing_data["annotation"]:
                signal_data["annotation"] = existing_data["annotation"]
                self._dump_annotation()
            self.data[sha] = signal_data
            os.remove(os.path.join(self.watch_dir, existing_data["file_name"]))
        else:
            os.remove(path)

    def _encode_annotation(self, annotation):
        return np.isin(list(self.annotation_count_dict.keys()), annotation).astype(int)

    def _dump_annotation(self):
        print("Dump call")
        annotations = []
        for sha, signal_data in self.data.items():
            if signal_data["annotation"]:
                annotations.append((signal_data["file_name"], self._encode_annotation(signal_data["annotation"])))
        if annotations:
            index, annotations = zip(*annotations)
            annotations = np.array(annotations)
            df = pd.DataFrame(annotations, index=index, columns=list(self.annotation_count_dict.keys())).reset_index()
            df.to_feather(self.submitted_annotation_path)

    def _get_annotation_list(self, data, meta):
        data = [{"id": group, "annotations": annotations} for group, annotations in self.annotation_dict.items()]
        return dict(data=data, meta=meta)

    def _get_common_annotation_list(self, data, meta):
        N_TOP = 5
        STOPWORDS = ["Другое"]
        DEFAULTS = ["Нормальный ритм"]
        positive_count = {annotation: count for annotation, count in self.annotation_count_dict.items()
                          if count > 0 and not any(word in annotation for word in STOPWORDS)}
        annotations = sorted(positive_count, key=lambda x: (-positive_count[x], x))
        annotations = (annotations + DEFAULTS)[:N_TOP]
        data["annotations"] = annotations
        return dict(data=data, meta=meta)

    def _get_ecg_list(self, data, meta):
        ecg_list = []
        for sha, signal_data in self.data.items():
            ecg_data = {
                "id": sha,
                "timestamp": signal_data["meta"]["timestamp"],
                "is_annotated": bool(signal_data["annotation"]),
            }
            ecg_list.append(ecg_data)
        ecg_list = sorted(ecg_list, key=lambda val: val["timestamp"], reverse=True)
        for ecg_data in ecg_list:
            ecg_data["timestamp"] = ecg_data["timestamp"].strftime("%d.%m.%Y %H:%M:%S")
        return dict(data=ecg_list, meta=meta)

    def _get_item_data(self, data, meta):
        sha = data.get("id")
        if sha is None or sha not in self.data:
            raise ValueError("Invalid sha {}".format(sha))
        signal_data = self.data[sha]
        data["signal"] = signal_data["signal"]
        data["frequency"] = signal_data["meta"]["fs"]
        data["units"] = signal_data["meta"]["units"]
        data["signame"] = signal_data["meta"]["signame"]
        data["annotation"] = signal_data["annotation"]
        return dict(data=data, meta=meta)

    def _set_annotation(self, data, meta):
        sha = data.get("id")
        if sha is None or sha not in self.data:
            raise ValueError("Invalid sha {}".format(sha))
        annotation = data.get("annotation")
        if annotation is None:
            raise ValueError("Empty annotation")
        unknown_annotation = [ann for ann in annotation if ann not in self.annotation_count_dict]
        if unknown_annotation:
            raise ValueError("Unknown annotation: {}".format(", ".join(unknown_annotation)))
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
        data = OrderedDict()
        for sha, signal_data in self.data.items():
            if signal_data["file_name"] != src:
                data[sha] = signal_data
            else:
                need_dump = bool(signal_data["annotation"])
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
                need_dump = bool(signal_data["annotation"])
        if need_dump:
            self._dump_annotation()
        print(len(self.data), [signal_data["file_name"] for sha, signal_data in self.data.items()])
        self.namespace.on_ECG_GET_LIST({}, {})
