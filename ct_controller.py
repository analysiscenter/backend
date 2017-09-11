import os
import sys

from lung_cancer.dataset import Dataset as ds
from lung_cancer.dataset import FilesIndex
from lung_cancer import CTImagesModels

# path to pretrained unet
PRETRAINED_UNET = ''

# glob-mask of patients that interest us
LUNA_DIR = ''

# dir with stored model
PRETRAINED_UNET_DIR = ''

class CtController:
	def __init__(self):
		self.ppl_load_scan = _
		self.ppl_inference_scan = _

		keras_unet_config = {"keras_unet": PRETRAINED_UNET_DIR}
