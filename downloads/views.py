import os
import re
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

USER_DIR = getattr(settings, 'DOWNLOAD_USERS_DIR', '/users')
ARCHIVE_DIR = getattr(settings, 'DOWNLOAD_ARCHIVE_DIR', '/archive')
CACHE_DIR = getattr(settings, 'DOWNLOAD_CACHE_DIR', '/cache')
FRONTEND = getattr(settings, 'DOWNLOAD_FRONTEND', 'xsendfile')

USER_ROOT = getattr(settings, 'LDAP_USER_ROOT', '/users')
ARCHIVE_ROOT = getattr(settings, 'ARCHIVE_ROOT', '/users')

ROOT_RE = re.compile(rf'^{USER_ROOT}')
ARCHIVE_RE = re.compile(rf'^{USER_DIR}')

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
        path = request.POST.get('path')
        obj = SecurePath()
        full_path = path if path.startswith(USER_ROOT) else os.path.join(USER_ROOT, path)
        obj.path = re.sub(ROOT_RE, USER_DIR, full_path)
        obj.save()
        return JsonResponse({'key': obj.key})


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


def send_snapshot(request, key, path):
    directory = utils.get_download_path(key)
    file_paths = []
    if not directory:
        file_paths.append(Path(utils.get_missing_snapshot()))
    else:
        file_paths.append((Path(directory) / path).absolute())
        file_paths.append((Path(re.sub(ARCHIVE_RE, ARCHIVE_DIR, directory)) / path).absolute())

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
            frame_paths = [
                Path(directory).absolute() / path,
                Path(re.sub(ARCHIVE_RE, ARCHIVE_DIR, directory)).absolute() / path
            ]

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

    full_paths = [
        Path(document_root).absolute() / clean_path(path),
        Path(re.sub(ARCHIVE_RE, ARCHIVE_DIR, document_root)).absolute() / clean_path(path),
    ]
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

    full_paths = [
        Path(document_root).absolute(),
        Path(re.sub(ARCHIVE_RE, ARCHIVE_DIR, document_root)).absolute(),
    ]

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
