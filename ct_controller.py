import os
import sys
import numpy as np

from lung_cancer.dataset import FilesIndex, Pipeline
from lung_cancer import CTImagesModels

# model config
unet_path = '/notebooks/segm/analysis/conf/model_best_unet_tiversky_2017-8-4-21-57.hdf5'
unet_loss = 'tiversky'
config = {'loss': unet_loss, 'path': unet_path}

# chosen id-nums
ixs_nums = np.array([714, 297, 299, 672])
lunaix = FilesIndex(path= '/notebooks/data/MRT/luna/s*/*.mhd', no_ext=True)
all_ixs = lunaix.create_subset(lunaix.index[[714, 297, 299, 672]])

class CtController:
    def __init__(self):
        # dict of patients indices
        self.ct_list = dict(zip([str(i) for i in range(len(all_ixs))], [all_ixs.indices]))

        self.ppl_load_scan = _
        self.ppl_inference_scan = _

        keras_unet_config = {"keras_unet": PRETRAINED_UNET_DIR}
