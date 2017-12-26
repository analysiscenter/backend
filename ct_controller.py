import os
import sys
import numpy as np
import pandas as pd
from time import sleep

from lung_cancer.dataset import FilesIndex, Pipeline, Dataset
from lung_cancer import CTImagesModels as CTIM
from lung_cancer import CTImagesBatch as CTIB
from lung_cancer import CTImagesMaskedBatch as CTIMB
from tqdm import tqdm

# chosen ixs
lunapath = os.path.join('.', 'data', 'ct', 'scans', '*')
all_ixs = FilesIndex(path=lunapath, dirs=True)

# args of actions in pipelines
# item demonstration
RENDER_SHAPE = (32, 64, 64)

# inference
USPACING_SHAPE = (300, 400, 400)
SPACING = (1., 1., 1.)
METHOD = 'scipy'
STRIDES = (32, 64, 64)
nodules_df = pd.read_csv(os.path.join('.', 'data', 'ct', 'annotations', 'annotations.csv'))

class CtController:
    def __init__(self):
        # set up the correspondance between ids and backend names
        self.ct_names = dict(zip([str(i) for i in range(len(all_ixs))], all_ixs.indices))

        # pipelines
        # load and resize scan to low res for render
        self.ppl_render_scan = (Pipeline()
                                    .load(fmt='blosc', components=['images', 'spacing', 'origin'])
                                    .resize(shape=RENDER_SHAPE))

        # load scan and perform inference
        args_uspacing = dict(shape=USPACING_SHAPE, spacing=SPACING, method=METHOD)

        # note that this pipeline puts predictions in masks-component
        self.ppl_predict_scan = (Pipeline()
                                    .load(fmt='blosc', components=['images', 'masks', 'spacing', 'origin'])
                                    .fetch_nodules_info(nodules_df))

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
        ct_list = [dict(name='Patient ' + key, id=key) for key in sorted(self.ct_names)]
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
        print(bch.images.dtype)

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

        bch.images = bch.masks * 255
        bch.masks = None
        bch.resize(shape=RENDER_SHAPE)

        # nodules info in pixel coords
        nodules = (bch.nodules.nodule_center - bch.nodules.origin) / bch.nodules.spacing
        diams = bch.nodules.nodule_size / bch.nodules.spacing
        nodules = np.rint(np.hstack([nodules, diams])).astype(np.int)
        item_data = dict(mask=bch.images.tolist(), nodules=nodules.tolist())
        # update and fetch data dict
        print('DONE PREDICTING')
        res = dict(data={**item_data, **data}, meta=meta)
        return res
