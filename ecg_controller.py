import os
import sys
import re
from functools import partial

import numpy as np

sys.path.append("./ecg/")
from cardio import dataset as ds
from cardio.dataset import B, V
from cardio import EcgDataset
from cardio.models import HMModel, DirichletModel, concatenate_ecg_batch
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"


def prepare_batch(batch, model):
    X = np.concatenate([hmm_features[0].T for hmm_features in batch.hmm_features])
    lengths = [hmm_features.shape[2] for hmm_features in batch.hmm_features]
    return {"X": X, "lengths": lengths}


class EcgController:
    def __init__(self):
        self.ecg_path = os.path.join(os.getcwd(), "data", "ecg_data")
        ecg_names = [f for f in sorted(os.listdir(self.ecg_path)) if re.match(r"A.*\.hea", f)]
        key_len = len(str(len(ecg_names) + 1))
        self.ecg_names = {str(i + 1).zfill(key_len): f for i, f in enumerate(ecg_names)}

        BATCH_SIZE = 1

        self.ppl_load_signal = (
            ds.Pipeline()
              .load(fmt='wfdb', components=["signal", "meta"])
              .flip_signals()
              .run(batch_size=BATCH_SIZE, shuffle=False, drop_last=False, n_epochs=1, lazy=True)
        )

        dirichlet_config = {
            "build": False,
            "load": {"path": os.path.join(os.getcwd(), "data", "ecg_models", "dirichlet")},
        }

        self.ppl_predict_af = (
            ds.Pipeline()
              .init_model("static", DirichletModel, name="dirichlet", config=dirichlet_config)
              .init_variable("predictions_list", init_on_each_run=list)
              .load(fmt="wfdb", components=["signal", "meta"])
              .flip_signals()
              .split_signals(2048, 2048)
              .predict_model("dirichlet", make_data=partial(concatenate_ecg_batch, return_targets=False),
                             fetches="predictions", save_to=V("predictions_list"), mode="e")
              .run(batch_size=BATCH_SIZE, shuffle=False, drop_last=False, n_epochs=1, lazy=True)
        )

        hmm_config = {
            "build": False,
            "load": {"path": os.path.join(os.getcwd(), "data", "ecg_models", "hmm", "hmm_model_old.dill")}
        }

        self.ppl_predict_states = (
            ds.Pipeline()
              .init_model("static", HMModel, name="HMM", config=hmm_config)
              .load(fmt="wfdb", components=["signal", "meta"])
              .cwt(src="signal", dst="hmm_features", scales=[4, 8, 16], wavelet="mexh")
              .standartize(axis=-1, src="hmm_features", dst="hmm_features")
              .predict_model("HMM", make_data=prepare_batch, save_to=B("hmm_annotation"))
              .calc_ecg_parameters(src="hmm_annotation")
              .run(batch_size=BATCH_SIZE, shuffle=False, drop_last=False, n_epochs=1, lazy=True)
        )

    def build_ds(self, data):
        ecg_id = data.get("id")
        ecg_name = self.ecg_names.get(ecg_id)
        if ecg_id is None or ecg_name is None:
            raise ValueError("Invalid ecg name")
        eds = EcgDataset(path=os.path.join(self.ecg_path, ecg_name), no_ext=True, sort=True)
        return eds

    def get_list(self, data, meta):
        ecg_list = [dict(id=k, name=self.ecg_names[k].split(".")[0]) for k in sorted(self.ecg_names)]
        return dict(data=ecg_list, meta=meta)

    def get_item_data(self, data, meta):
        eds = self.build_ds(data)
        batch = (eds >> self.ppl_load_signal).next_batch()
        data["signal"] = batch.signal[0].ravel().tolist()
        data["frequency"] = batch.meta[0]["fs"]
        data["units"] = batch.meta[0]["units"][0]
        return dict(data=data, meta=meta)

    def get_inference(self, data, meta):
        eds = self.build_ds(data)
        batch = (eds >> self.ppl_predict_states).next_batch()
        signal_meta = batch.meta[0]
        inference = {
            "heart_rate": signal_meta["hr"],
            "qrs_interval": signal_meta["qrs"],
            "qt_interval": signal_meta["qt"],
            "pq_interval": signal_meta["pq"],
            "p_segments": signal_meta["p_segments"].tolist(),
            "t_segments": signal_meta["t_segments"].tolist(),
            "qrs_segments": signal_meta["qrs_segments"].tolist(),
        }
        ppl_predict_af = (eds >> self.ppl_predict_af).run()
        inference["af_prob"] = float(ppl_predict_af.get_variable("predictions_list")[0]["target_pred"]["A"])
        data["inference"] = inference
        return dict(data=data, meta=meta)
