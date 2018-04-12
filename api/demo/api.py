from .ecg_controller import EcgController
from .ct_controller import CtController
from ..api_base import BaseNamespace

# init controller objects
ecg = EcgController()
ct = CtController()


class DemoNamespace(BaseNamespace):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def on_ECG_GET_LIST(self, data, meta):
        self._safe_call(ecg.get_list, data, meta, "ECG_GET_LIST", "ECG_GOT_LIST")

    def on_ECG_GET_ITEM_DATA(self, data, meta):
        self._safe_call(ecg.get_item_data, data, meta, "ECG_GET_ITEM_DATA", "ECG_GOT_ITEM_DATA")

    def on_ECG_GET_INFERENCE(self, data, meta):
        self._safe_call(ecg.get_inference, data, meta, "ECG_GET_INFERENCE", "ECG_GOT_INFERENCE")

    def on_CT_GET_LIST(self, data, meta):
        self._safe_call(ct.get_list, data, meta, "CT_GET_LIST", "CT_GOT_LIST")

    def on_CT_GET_ITEM_DATA(self, data, meta):
        self._safe_call(ct.get_item_data, data, meta, "CT_GET_ITEM_DATA", "CT_GOT_ITEM_DATA")

    def on_CT_GET_INFERENCE(self, data, meta):
        self._safe_call(ct.get_inference, data, meta, "CT_GET_INFERENCE", "CT_GOT_INFERENCE")
