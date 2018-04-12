from watchdog.observers import Observer

from .handler import EcgDirectoryHandler
from ..api_base import BaseNamespace


class AnnotationNamespace(BaseNamespace):
    def __init__(self, watch_dir, submitted_annotation_path, annotation_list_path, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.handler = EcgDirectoryHandler(self, watch_dir, submitted_annotation_path, annotation_list_path,
                                           ignore_directories=True)
        observer = Observer()
        observer.schedule(self.handler, watch_dir)
        observer.start()

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
