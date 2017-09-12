import os
import sys
import numpy as np
import pandas as pd

from lung_cancer.dataset import FilesIndex, Pipeline, Dataset
from lung_cancer import CTImagesModels as CTIM
from lung_cancer import CTImagesBatch as CTIB
from lung_cancer import CTImagesMaskedBatch as CTIMB

# model config
unet_path = '/notebooks/segm/analysis/conf/model_best_unet_tiversky_2017-8-4-21-57.hdf5'
unet_loss = 'tiversky'
config = {'loss': unet_loss, 'path': unet_path}

# chosen id-nums
ixs_nums = np.array([714, 297, 299, 672])
lunaix = FilesIndex(path= '/notebooks/data/MRT/luna/s*/*.mhd', no_ext=True)
ixs_arr = lunaix.indices[ixs_nums]
all_ixs = lunaix.create_subset(ixs_arr)

# args of actions in pipelines
# item demonstration
RENDER_SHAPE = (32, 64, 64)

# inference
USPACING_SHAPE = (300, 400, 400)
SPACING = (1., 1., 1.)
METHOD = 'scipy'
STRIDES = (32, 64, 64)
nodules_df = pd.read_csv('/notebooks/data/MRT/luna/CSVFILES/annotations.csv')

class CtController:
    def __init__(self):
        # set up the correspondance between ids and backend names
        self.ct_names = dict(zip([str(i) for i in range(len(all_ixs))], all_ixs.indices))

        # pipelines

        # load and resize scan to low res for render
        self.ppl_render_scan = (Pipeline()
                                    .load(fmt='raw')
                                    .resize(shape=RENDER_SHAPE)
                                    .normalize_hu())

        # load scan and perform inference
        args_uspacing = dict(shape=USPACING_SHAPE, spacing=SPACING, method=METHOD)
        args_pred_on_scan = dict(model_name='keras_unet', strides=STRIDES,
                                 dim_ordering='channels_first', y_component='masks')
        # note that this pipeline puts predictions in masks-component
        self.ppl_predict_scan = (Pipeline(config=config)
                                    .load(fmt='raw')
                                    .unify_spacing(**args_uspacing)
                                    .double_normalize_hu()
                                    .predict_on_scan(**args_pred_on_scan))

    def build_item_ds(self, data):
        """ Auxilliary method for building dataset from one elem.

        Args:
            data: dict that contains id of scan (by key 'id') that is wrapped up in a
                dataset.

        Return:
            dataset containing one element.
        """
        # build index
        item_id = data.get('id')
        ix_arr = np.asarray([self.ct_names.get(item_id)])
        ix = all_ixs.create_subset(ix_arr)

        return Dataset(index=ix, batch_class=CTIM)

    def get_list(self, data, meta):
        """ Correspondence between ids and frontend names.
        """
        ct_list = [dict(name='Patient ' + key, id=key) for key in self.ct_names]
        return dict(data=ct_list, meta=meta)

    def get_item_data(self, data, meta):
        """ Get low-res scan-item prepared for rendering.

        Args:
            data: dict containing key 'id' with id of the scan for rendering.
            meta: additional info needed for communication between frontend and backend.

        NOTE: image, mask, nodules
        """
        item_ds = self.build_item_ds(data)
        bch = (item_ds >> self.ppl_render_scan).next_batch(1)
        item_data = dict(image=bch.images.tolist())

        # update and fetch the data-dict along with meta
        return dict(data={**item_data, **data}, meta=meta)

    def get_inference(self, data, meta):
        """ Get predicted mask resized to low-res for rendering along with nodules-list.

        Args:
            data: dict containing key 'id' with 'id' of the scan for inference.
            meta: additional info needed for communication between frontend and backend.
        """
        item_ds = self.build_item_ds(data)
        bch = (item_ds >> self.ppl_predict_scan).next_batch(1)

        # create two batches from masked batch for resize
        bch_scan, bch_predicted = CTIMB(bch.index), CTIB(bch.index)
        args_load = dict(fmt='ndarray', origin=bch.origin, spacing=bch.spacing, bounds=bch._bounds)

        bch_scan.load(**args_load, source=bch.images)
        bch_predicted.load(**args_load, source=bch.masks)

        # load nodules info and resize batches for rendering
        bch_scan.fetch_nodules_info(nodules_df)
        bch_scan = bch_scan.resize(shape=RENDER_SHAPE)
        bch_predicted = bch_predicted.resize(shape=RENDER_SHAPE)

        # nodules info in pixel coords
        nodules = (bch_scan.nodules.nodule_center - bch_scan.nodules.origin) / bch_scan.nodules.spacing
        diams = bch_scan.nodules.nodule_size / bch_scan.nodules.spacing
        nodules = np.hstack([nodules, diams])

        item_data = dict(mask=bch_predicted.images.tolist(), nodules=nodules.tolist())

        # update and fetch data dict
        return dict(data={**item_data, **data}, meta=meta)
