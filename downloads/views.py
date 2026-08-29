import os
import re
import json
import subprocess
from pathlib import Path, PurePath

from django import http
from django.conf import settings
from django.http import HttpResponse, StreamingHttpResponse, JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
from django.views.static import serve

import downloads.utils as utils
from downloads.models import SecurePath

DOWNLOAD_DIRS = getattr(settings, 'DOWNLOAD_DIRS', [])          # directories from which downloads are allowed
USER_ROOT = getattr(settings, 'USER_ROOT', '/users')            # where to find relative directories starting with user
SUBSTITUTE_DIRS = getattr(settings, 'SUBSTITUTE_DIRS', [])      # list of directories that are equivalent to the download
CACHE_DIR = getattr(settings, 'DOWNLOAD_CACHE_DIR', '/cache')
FRONTEND = getattr(settings, 'DOWNLOAD_FRONTEND', 'xsendfile')
BRIGHTNESS = {'xl': 0.25, 'nm': 1.0, 'dk': 1.5, 'lt': 0.5}

import logging

logging.basicConfig()
logger = logging.getLogger(__name__)


def create_cache_dir(key):
    directory = Path(CACHE_DIR) / key
    if not directory.exists():
        directory.mkdir(parents=True, exist_ok=True)
    return directory


@method_decorator(csrf_exempt, name='dispatch')
class CreatePath(View):

    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        path = data.get('path') or ''
        path = path if path.startswith('/') else os.path.join(USER_ROOT, path)
        key = None
        if any(path.startswith(d) for d in DOWNLOAD_DIRS):
            obj = SecurePath()
            obj.path = path
            obj.save()
            key = obj.key
        return JsonResponse({'key': key})


def send_uncompressed_file(request, key, full_path):
    create_cache_dir(key)
    uncompressed_file = full_path.name.rstrip('.gz')
    cached_file = Path(CACHE_DIR) / key / uncompressed_file
    cmd = f'gunzip {full_path} {cached_file}'
    try:
        subprocess.check_call(cmd.split())
    except subprocess.CalledProcessError:
        return http.HttpResponseNotFound()
    return send_raw_file(request, cached_file)


def send_raw_file(request, full_path, attachment=False):
    """
    Send a file using mod_xsendfile or similar functionality.
    Use django's static serve option for development servers
    :param request: Django request object
    :param full_path: Full path to file
    :param attachment: Boolean to force download
    """

    file_path = Path(full_path)

    if not file_path.exists():
        logger.warning("Path not found: {}".format(file_path))
        return http.HttpResponseNotFound()

    if FRONTEND == "xsendfile":
        response = HttpResponse()
        response['X-Sendfile'] = str(file_path)
        if attachment:
            response['Content-Disposition'] = f'attachment; filename={file_path.name}'

        # Unset the Content-Type as to allow for the webserver
        # to determine it.
        response['Content-Type'] = ''

    elif FRONTEND == "xaccelredirect":
        response = HttpResponse()
        response['X-Accel-Redirect'] = str(file_path)

        if attachment:
            response['Content-Disposition'] = 'attachment; filename=%s' % os.path.basename(file_path)
        response['Content-Type'] = ''

    else:
        dirname = str(file_path.parent)
        path = file_path.name

        # "Serving file %s in directory %s through django static serve." % (path, dirname)
        response = serve(request, path, dirname)

    return response


def make_alternates(path):
    """
    Generate a list of alternate paths for a given path
    :param path: The Path to generate alternates for
    :return: List of alternate paths
    """
    path_str = str(path)

    alternates = [path]
    # find which string path starts with, then replace that string with the
    # others in the list of substitutes
    for sub in SUBSTITUTE_DIRS:
        if re.match(rf'^{sub}', path_str):
            regex = re.compile(rf'^{sub}')
            for repl in set(SUBSTITUTE_DIRS) - {sub}:
                alternates.append(Path(re.sub(regex, repl, path_str)))
            break
    return alternates


def send_snapshot(request, key, path):
    directory = utils.get_download_path(key)
    file_paths = []
    if directory:
        snapshot_path = (Path(directory) / path).absolute()
        suffixes = ['.webp', '.png', '.gif']
        for suffix in suffixes:
            file_paths.extend(make_alternates(snapshot_path.with_suffix(suffix)))

    try:
        missing_snapshot = utils.get_missing_snapshot()
        if missing_snapshot:
            file_paths.append(Path(missing_snapshot))
    except (FileNotFoundError, IOError):
        pass

    for file_path in file_paths:
        if file_path.exists():
            return send_raw_file(request, file_path)
    else:
        return http.HttpResponseNotFound()


def clean_path(path):
    if path.startswith('/'):
        path = path[1:]
    return path


class SendFrame(View):

    def get(self, request, *args, **kwargs):
        key = kwargs.get('key')
        path = kwargs.get('path')
        brightness = kwargs.get('brightness')
        directory = utils.get_download_path(key)
        cache_image = Path(CACHE_DIR) / key / clean_path(PurePath(path).stem) / f'{brightness}.png'
        if cache_image.exists():
            return send_raw_file(request, cache_image)
        elif not directory:
            return send_raw_file(request, utils.get_missing_frame())
        else:
            frame_paths = make_alternates(Path(directory).absolute() / path)

            for frame_path in frame_paths:
                if frame_path.exists() or re.match(r'\d+', frame_path.name):
                    if not cache_image.parent.exists():
                        cache_image.parent.mkdir(parents=True, exist_ok=True)
                    utils.create_png(frame_path, cache_image, BRIGHTNESS.get(brightness, 0.0))
                    return send_raw_file(request, cache_image)
            return send_raw_file(request, utils.get_missing_frame())


def send_file(request, key, path):
    document_root = utils.get_download_path(key)
    if not document_root:
        return http.HttpResponseNotFound()

    full_paths = make_alternates(Path(document_root).absolute() / clean_path(path))
    for full_path in full_paths:
        if full_path.exists():
            return send_raw_file(request, full_path)
        elif full_path.with_suffix(full_path.suffix + '.gz').exists():
            return send_uncompressed_file(request, key, full_path)
    else:
        return http.HttpResponseNotFound()


def send_archive(request, key, path):  # Add base parameter and another url
    document_root = utils.get_download_path(key)
    if not document_root:
        return http.HttpResponseNotFound()

    full_paths = make_alternates(Path(document_root).absolute())

    for full_path in full_paths:
        if full_path.exists():
            process = subprocess.Popen(
                ['tar', '-czf', '-', full_path.name],
                cwd=full_path.parent,
                stdout=subprocess.PIPE
            )
            response = StreamingHttpResponse(process.stdout, content_type='application/x-gzip')
            response['Content-Disposition'] = f'attachment; filename={path}'
            return response
    else:
        return http.HttpResponseNotFound()
