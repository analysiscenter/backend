import os
import sys

import tensorflow as tf

from ecg import ds, ModelEcgBatch
from ecg.ecg import models
sys.modules["ecg.models"] = models
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"

class EcgController:
    def __init__(self):
        self.ecg_path = os.path.join(os.getcwd(), "data", "ecg_data")
        self.ecg_names = {
            "1": "A00001.hea",
            "2": "A00002.hea",
            "3": "A00004.hea",
            "4": "A00005.hea",
            "5": "A00008.hea",
            "6": "A00013.hea",
        }

        dirichlet_path = os.path.join(os.getcwd(), "data", "ecg_models", "dirichlet")
        dirichlet_last_path = tf.train.latest_checkpoint(dirichlet_path)
        dirichlet_config = {
            "graph_path": dirichlet_last_path + ".meta",
            "checkpoint_path": dirichlet_last_path,
            "classes_path": dirichlet_last_path + ".dill"
        }
        hmm_config = {
            "path": os.path.join(os.getcwd(), "data", "ecg_models", "hmm", "HMMAnnotation.dill"),
        }
        config = {
            "dirichlet_pretrained": dirichlet_config,
            "hmm_annotation_pretrained": hmm_config,
        }

        BATCH_SIZE = 1

        self.ppl_load_signal = (
            ds.Pipeline()
              .load(fmt='wfdb', components=["signal", "meta"])
              .flip_signals()
              .get_signal_meta(var_name="signal")
              .run(batch_size=BATCH_SIZE, shuffle=False, drop_last=False, n_epochs=1, lazy=True)
        )

        self.ppl_predict_af = (
            ds.Pipeline(config=config)
              .init_model("dirichlet_pretrained")
              .load(fmt="wfdb", components=["signal", "meta"])
              .flip_signals()
              .segment_signals(2048, 512)
              .predict_on_batch("dirichlet_pretrained", predictions_var_name="af_prediction")
              .run(batch_size=BATCH_SIZE, shuffle=False, drop_last=False, n_epochs=1, lazy=True)
        )

        self.ppl_predict_states = (
            ds.Pipeline(config=config)
              .init_model("hmm_annotation_pretrained")
              .load(fmt='wfdb', components=["signal", "annotation", "meta"])
              .flip_signals()
              .generate_hmm_features(cwt_scales=[4, 8, 16], cwt_wavelet="mexh")
              .predict_on_batch("hmm_annotation_pretrained")
              .calc_ecg_parameters()
              .get_signal_annotation_results(var_name="states_prediction")
              .run(batch_size=BATCH_SIZE, shuffle=False, drop_last=False, n_epochs=1, lazy=True)
        )

    def build_ds(self, data):
        ecg_id = data.get("id")
        ecg_name = self.ecg_names.get(ecg_id)
        if ecg_id is None or ecg_name is None:
            raise ValueError("Invalid ecg name")
        index = ds.FilesIndex(path=os.path.join(self.ecg_path, ecg_name), no_ext=True, sort=True)
        eds = ds.Dataset(index, batch_class=ModelEcgBatch)
        return eds

    def get_list(self, data, meta):
        ecg_list = [dict(id=k, name="Patient " + self.ecg_names[k].split(".")[0]) for k in sorted(self.ecg_names)]
        return dict(data=ecg_list, meta=meta)

    def get_item_data(self, data, meta):
        eds = self.build_ds(data)
        (eds >> self.ppl_load_signal).run()
        item_data = self.ppl_load_signal.get_variable("signal")[0]
        item_data["signal"] = item_data["signal"].ravel().tolist()
        item_data["units"] = item_data["units"][0]
        return dict(data={**data, **item_data}, meta=meta)

    def get_inference(self, data, meta):
        eds = self.build_ds(data)
        (eds >> self.ppl_predict_states).run()
        inference = self.ppl_predict_states.get_variable("states_prediction")[0]
        for k in ("p_segments", "t_segments", "qrs_segments"):
            inference[k] = inference[k].tolist()
        (eds >> self.ppl_predict_af).run()
        inference["af_prob"] = float(self.ppl_predict_af.get_variable("af_prediction")[0]["target_pred"]["A"])
        return dict(data={**data, **inference}, meta=meta)
