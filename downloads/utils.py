from django.conf import settings
from django.shortcuts import get_object_or_404

from .models import SecurePath

import os
import cv2
import numpy
import matplotlib
import shutil

from mxio import read_image
from skimage import measure, exposure
from matplotlib import pyplot as plt


MAX_PERCENTILE = 99.985


DATA_DIR = os.path.join(settings.BASE_DIR, 'data')
CACHE_DIR = getattr(settings, 'DOWNLOAD_CACHE_DIR', '/tmp')


def get_download_path(key):
    """Convenience method to return a path for a key"""
    obj = SecurePath.objects.filter(key=key).first()
    return obj.path if obj else None


def downsample(frame, size, func=numpy.max):   
    factor = min(frame.size.x // size, frame.size.y//size)
    data = frame.data
    kernel = (factor, factor)
    data = measure.block_reduce(data, block_size=kernel, func=func)
    h, w = data.shape
    cx, cy = w//2, h//2
    hw = size // 2
    
    x0, y0 = cx - hw, cy - hw
    x1, y1 = x0 + size, y0 + size
    return data[y0:y1, x0:x1]  


def load_image(filename, brightness=0.0, resolution=(1024, 1024)):
    """
    Read file and return an PIL image of desired resolution histogram
    :param filename: Image File (e.g. filename.img, filename.cbf)
    :param brightness: float (1.5=dark; -0.5=light)
    :param resolution: output size
    :return: resized PIL image
    """

    obj = read_image(filename)
    frame = obj.frame
    size = min(resolution)

    img = downsample(frame, size, func=numpy.max)   
    hi = numpy.percentile(img, MAX_PERCENTILE)
    image =  exposure.rescale_intensity(img, in_range=(0, hi), out_range=(0, 255)).astype(numpy.uint8)
    
    return image


def array_to_png(data, filename, cmap='magma'):
    # Create a figure without default frames
    h, w = data.shape
    dpi=100
    fig  = plt.figure(frameon=False)
    fig.set_size_inches(h/dpi, w/dpi)

    ax = plt.Axes(fig, [0., 0., 1., 1.])
    ax.set_axis_off()
    fig.add_axes(ax)
    ax.imshow(data, cmap=cmap)
    fig.savefig(filename, bbox_inches='tight', pad_inches=0, dpi=dpi)
    plt.close()


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
    array_to_png(img_info, output)


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
