import os
import sys
import re

CURRENT_PATH = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(1, os.path.join(CURRENT_PATH, "ecg"))
from cardio import dataset as ds
from cardio import EcgDataset
from cardio.pipelines import dirichlet_predict_pipeline, hmm_predict_pipeline
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"


class EcgController:
    def __init__(self):
        self.ecg_path = os.path.join(CURRENT_PATH, "data", "ecg_data")
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

        dirichlet_path = os.path.join(CURRENT_PATH, "data", "ecg_models", "dirichlet")
        self.ppl_predict_af = dirichlet_predict_pipeline(dirichlet_path, batch_size=BATCH_SIZE)

        hmm_path = os.path.join(CURRENT_PATH, "data", "ecg_models", "hmm", "hmm_model_old.dill")
        self.ppl_predict_states = hmm_predict_pipeline(hmm_path, batch_size=BATCH_SIZE)

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
