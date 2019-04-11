import os
import pickle
import numpy
import shutil
from PIL import Image

from django.conf import settings
from imageio import read_image
from imageio.utils import stretch

DATA_DIR = os.path.join(settings.BASE_DIR, 'data')
COLORMAPS = pickle.load(file(os.path.join(DATA_DIR, 'colormaps.data')))
CACHE_DIR = getattr(settings, 'DOWNLOAD_CACHE_DIR', '/tmp')

# Modify default colormap to add overloaded pixel effect
COLORMAPS['gist_yarg'][-1] = 0
COLORMAPS['gist_yarg'][-2] = 0
COLORMAPS['gist_yarg'][-3] = 255
GAMMA_SHIFT = 3.5


def load_image(filename, gamma_offset=0.0, resolution=(1024, 1024)):
    """
    Read file and return an PIL image of desired resolution histogram stretched by the
    requested gamma_offset
    :param filename: Image File (e.g. filename.img, filename.cbf)
    :param gamma_offset: default 0.0
    :param resolution: output size
    :return: resized PIL image
    """

    image_obj = read_image(filename)
    gamma = image_obj.header['gamma']
    disp_gamma = gamma * numpy.exp(gamma_offset + GAMMA_SHIFT)/30.0
    raw_img = image_obj.image.convert('I')
    lut = stretch(disp_gamma)
    raw_img = raw_img.point(list(lut), 'L')
    raw_img.putpalette(COLORMAPS['gist_yarg'])
    return raw_img.resize(resolution, Image.ANTIALIAS)


def create_png(filename, output, brightness, resolution=(1024, 1024)):
    """
    Generate png in output using filename as input with specified brightness
    and resolution. default resolution is 1024x1024
    creates a directory for output if none exists
    :param filename: Image File (e.g. filename.img, filename.cbf)
    :param output: PNG Image Filename
    :param brightness: float (1.5=dark; -0.5=light)
    :param resolution: output size
    :return: PNG Image
    """

    img_info = load_image(filename, brightness, resolution)
    dir_name = os.path.dirname(output)
    if not os.path.exists(dir_name) and dir_name != '':
        os.makedirs(dir_name)
    img_info.save(output, 'PNG')


def get_missing_image(src='frame-missing.png'):
    """Return full path to missing file placeholder"""
    missing_file = os.path.join(CACHE_DIR, src)
    src_file = os.path.join(DATA_DIR, src)
    if not os.path.exists(missing_file):
        shutil.copy(src_file, missing_file)
    return missing_file


def get_missing_frame():
    return get_missing_image(src='frame-missing.png')


def get_missing_snapshot():
    return get_missing_image(src='snapshot-missing.gif')