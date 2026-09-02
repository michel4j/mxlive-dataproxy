import mxio
from django.conf import settings
from django.shortcuts import get_object_or_404

from .models import SecurePath

import os
import numpy
import matplotlib
import shutil

from mxio import read_image, DataSet
from skimage import measure, exposure
from skimage.util import img_as_float
from skimage.morphology import disk, dilation
from matplotlib import pyplot as plt


MAX_PERCENTILE = 99.985
GAMMA = 0.4
GAIN = 5
SIZE = 1024

DATA_DIR = os.path.join(settings.BASE_DIR, 'data')
CACHE_DIR = getattr(settings, 'DOWNLOAD_CACHE_DIR', '/tmp')
FRAME_COLORMAP = getattr(settings, 'DOWNLOAD_FRAME_COLORMAP', 'gist_yarg')


def get_download_path(key):
    """Convenience method to return a path for a key"""
    obj = SecurePath.objects.filter(key=key).first()
    return obj.path if obj else None


def downsample(frame: mxio.ImageFrame, size: int = SIZE, func=numpy.max):
    """
    Downsample a diffraction frame and return a 2D array of shape (size, size). Enhances spot visibility
    at smaller image sizes
    :param frame: Source ImageFrame
    :param size: Target Image Size, will clip on-square images to (size, size) after conversion
    :param func: Reduction function applied to the frame
    :return: 2D array of shape (size, size)
    """
    factor = min(frame.size.x // size, frame.size.y // size)
    data = img_as_float(frame.data)
    kernel = (factor, factor)

    data = measure.block_reduce(data, block_size=kernel, func=func)
    data = dilation(data, footprint=disk(1.5))

    h, w = data.shape
    cx, cy = w // 2, h // 2
    hw = size // 2

    x0, y0 = cx - hw, cy - hw
    x1, y1 = x0 + size, y0 + size
    data = data[y0:y1, x0:x1]
    return data


def frame_to_png(path, filename, brightness=0.0, size=SIZE, cmap='gist_yarg'):
    """
    Convert a Diffraction frame to a lower resolution PNG image, adjusting the histogram
    to improve visibility of spots
    :param path: Path to frame
    :param filename: Output filename of PNG
    :param brightness: brightness adjustment factor [-0.2 ... 0.2]
    :param size: size of the resulting PNG
    :param cmap: Colurmap to use for rendering
    """
    dset = DataSet.new_from_file(path)
    frame = dset.frame

    data = downsample(frame, size)
    max_value = data[data < frame.cutoff_value].max()
    base_image = exposure.rescale_intensity(data, in_range=(0, max_value), out_range=(0, 1))
    corrected = exposure.adjust_gamma(base_image, gamma=(GAMMA + brightness), gain=GAIN)

    # Create a figure without default frames
    h, w = corrected.shape
    dpi = 10
    fig = plt.figure(frameon=False)
    fig.set_size_inches(h / dpi, w / dpi)

    # Add an axes that covers the entire figure (0 to 1 in width and height)
    ax = plt.Axes(fig, [0., 0., 1., 1.])
    ax.set_axis_off()
    fig.add_axes(ax)

    # Display the array with a colormap (e.g., 'viridis')
    img = ax.imshow(base_image, cmap=cmap)
    img.set_data(corrected)

    # Save the image without padding or borders
    fig.savefig(filename, bbox_inches='tight', pad_inches=0, dpi=dpi, pil_kwargs={"optimize": True})
    plt.close()


def create_png(filename: str, output: str, brightness: float, resolution=(1024, 1024)):
    """
    Generate png in output using filename as input with specified brightness
    and resolution. default resolution is 1024x1024
    creates a directory for output if none exists
    :param filename: Image File (e.g. filename.img, filename.cbf)
    :param output: PNG Image Filename
    :param brightness: float, gamma adjustment factor [-0.2 ... 0.2]
    :param resolution: output size
    :return: PNG Image file name
    """

    dir_name = os.path.dirname(output)
    if not os.path.exists(dir_name) and dir_name != '':
        os.makedirs(dir_name)
    size = min(resolution)
    frame_to_png(filename, output, brightness, size=size, cmap=FRAME_COLORMAP)


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
