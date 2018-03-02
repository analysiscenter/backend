import os
import sys
import re
import numpy as np
import base64

from imageio import imread
from skimage.transform import resize

sys.path.append('./meters')
from meters.batch import MeterBatch
from meters.pipelines import PipelineFactory
from meters.dataset import FilesIndex, Dataset, Pipeline, V, B
from meters.dataset.dataset.models.tf import TFModel

sys.path.append("./mt/")



# def add_bb(img, bb, c, width=3):
#     """Surrounds bounding box with given coordinates.

#     Parameters
#     ----------
#     img : array
#         image
#     bb : array with len 4
#         coordinates of bounding box
#     c : int
#         color
#     width : int, optional
#         Thickness of the bounding box.

#     Returns
#     -------
#     image with a circled bounding box.
#         """
#     lc, lr, w, h = bb.astype(np.int)
#     im_height = img.shape[0] - 1
#     im_width = img.shape[1] - 1
#     for i in range(width):
#         img[min(im_height,lr):min(im_height,lr)+i, min(im_width,lc):min(im_width,lc+w),:]=c
#         img[min(im_height,lr):min(im_height,lr+h), min(im_width,lc):min(im_width,lc)+i,:]=c
#         img[min(im_height,lr):min(im_height,lr+h), min(im_width,lc+w):min(im_width,lc+w)+i,:]=c
#         img[min(im_height,lr+h):min(im_height,lr+h)+i, min(im_width,lc):min(im_width,lc+w),:]=c
#     return img



class MtController:
    def __init__(self):
        self.meters_path = os.path.join(os.getcwd(), "mt")
        self.meters_filenames = sorted(os.listdir(self.meters_path))

        bbox_model_path = os.path.join(os.getcwd(), 'models', 'resnet_for_the_poor_last_epoch_iou69/')
        digits_model_path = os.path.join(os.getcwd(), 'models', 'VGG7/')

        self.output_shape = (500, 500)

        self.predict_pipeline = (Pipeline()
                                    .init_model('static', TFModel, 'model',
                                                 config={'load' : {'path' : bbox_model_path}, 'build': False})
                                    .init_model('static', TFModel, 'VGG7',
                                                 config={'load' : {'path' : digits_model_path}, 'build': False})
                                    .load(fmt='image', components='images')
                                    .resize((120, 120),  order=1, preserve_range=False,
                                            src='images', dst='resized_images')
                                    .init_variable('bbox_predictions', init_on_each_run=0)
                                    .predict_model('model', fetches=['predictions'],
                                                   feed_dict={'images': B('resized_images')},
                                                   save_to=[ B('pred_coordinates')])
                                    .get_global_coordinates(src='pred_coordinates', img='images')
                                    .update_variable('bbox_predictions', B('pred_coordinates'), mode='w')
                                    .crop_from_bbox(src='images', component_coord="pred_coordinates")
                                    .split_to_digits(n_digits=8)
                                    .init_variable('labels', init_on_each_run=0)
                                    .resize((64, 32),  order=1, preserve_range=False)
                                    .predict_model('VGG7', fetches='output_labels',
                                                   feed_dict={'images': B('images')},
                                                   save_to=V('labels'))
                                    )
    def build_ds(self, data):
        print('building DATASET')
        image_id = data.get("id")
        print("image_id", image_id)
        if image_id is None:
            raise ValueError("Invalid filename")
        return Dataset(index=FilesIndex(path=os.path.join(self.meters_path, image_id)), batch_class=MeterBatch)

    def get_list(self, data, meta):
        return dict(data=[dict(id=fname) for fname in self.meters_filenames], meta=meta)

    def _read_image(self, image_id):
        print(os.path.join(self.meters_path, image_id))
        return imread(os.path.join(self.meters_path, image_id))

    def get_item_data(self, data, meta):
        print('MtController get_item_data CALLED')
        image = self._read_image(data['id'])
        print('--------------------- image read')
        #-----------------
        # dset = self.build_ds(data)
        # print('dataset OK')
        # pred = self.predict_pipeline << dset
        # pred.next_batch(1)
        # print('pred OK')
        # bbox = pred.get_variable('bbox_predictions')[0] * np.tile(self.output_shape, 2) / np.tile(image.shape[1::-1], 2)
        # print('bbox OK', bbox)
        # labels = pred.get_variable('labels')
        # print('labels OK', labels)
        # image = resize(image, self.output_shape , preserve_range=True)
        # image = add_bb(image, bbox, c=[0,255,0], width=3)
        # print('add BBOX OK')
        #-----------------

 #       image = resize(image, self.output_shape , preserve_range=True)
 #       data['img'] = image.ravel().tolist()
        image_id = data['id']
        print('-'*10+'reading' + os.path.join(self.meters_path, image_id))
        with open(os.path.join(self.meters_path, image_id), 'rb') as f:
            img = base64.b64encode(bytearray(f.read()))
        print('-'*10 + 'success')
        data['src'] = img
        print('wrote to src')
        data['height'] = image.shape[0] 
        data['width'] = image.shape[1]
        print('wrote shape')
        return dict(data=data, meta=meta)

    def get_inference(self, data, meta):
        print('MtController get_inference CALLED')

        image = self._read_image(data['id'])
        self.output_shape = image.shape[:2]
        dset = self.build_ds(data)
        print('dataset has been built')
        pred = self.predict_pipeline << dset
        print('created pred')
        pred.next_batch(1)
        print('got next batch')
        print('------------\n', pred.get_variable('bbox_predictions')[0], '----------')
        print(image.shape, image.shape[1::-1])
        bbox = pred.get_variable('bbox_predictions')[0]
        #bbox = pred.get_variable('bbox_predictions')[0] * np.tile(self.output_shape, 2) / np.tile(image.shape[1::-1], 2)
        labels = pred.get_variable('labels')

        inference = {
            "bbox": bbox.tolist(),
            "value": ''.join(map(str, labels))
        }
        data["inference"] = inference
        print('MtController inference data', data)
        return dict(data=data, meta=meta)
