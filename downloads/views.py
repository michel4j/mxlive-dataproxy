from models import SecurePath
from django.conf import settings
from django import http
from django.http import HttpResponse, Http404, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.static import serve
from django.views.generic import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import os
import posixpath
import re
import glob
import subprocess
import urllib
import utils
from django.http import StreamingHttpResponse


USER_DIR = getattr(settings, 'DOWNLOAD_USERS_DIR', '/users')
ARCHIVE_DIR = getattr(settings, 'DOWNLOAD_ARCHIVE_DIR', '/archive')
CACHE_DIR = getattr(settings, 'DOWNLOAD_CACHE_DIR', '/cache')
FRONTEND = getattr(settings, 'DOWNLOAD_FRONTEND', 'xsendfile')

USER_ROOT = getattr(settings, 'LDAP_USER_ROOT', '/users')
ARCHIVE_ROOT = getattr(settings, 'ARCHIVE_ROOT', '/users')

ROOT_RE = re.compile('^{}'.format(USER_ROOT))
ARCHIVE_RE = re.compile('^{}'.format(USER_DIR))

BRIGHTNESS = {'xl': -1.5, 'nm': 0.0, 'dk': 1.5, 'lt': -0.5}

import logging
logging.basicConfig()
logger = logging.getLogger(__name__)


def create_cache_dir(key):
    dir_name = os.path.join(CACHE_DIR, key)
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)
    return dir_name


@method_decorator(csrf_exempt, name='dispatch')
class CreatePath(View):

    def post(self, request, *args, **kwargs):
        path = request.POST.get('path')
        obj = SecurePath()
        full_path =  path if path.startswith(USER_ROOT) else os.path.join(USER_ROOT, path)
        obj.path = re.sub(ROOT_RE, USER_DIR, full_path)
        obj.save()
        return JsonResponse({'key': obj.key})


def get_download_path(key):
    """Convenience method to return a path for a key"""
    obj = get_object_or_404(SecurePath, key=key)
    return obj.path


def send_uncompressed_file(request, key, full_path):
    create_cache_dir(key)
    _, zfile = os.path.split(full_path)
    cached_file = os.path.join(CACHE_DIR, key, zfile.strip('.gz'))
    cmd = 'gunzip {0} {1}'.format(full_path, cached_file)
    try:
        subprocess.check_call(cmd.split())
    except:
        return http.HttpResponseNotFound()
    return send_raw_file(request, cached_file)


def send_raw_file(request, full_path, attachment=False):
    """Send a file using mod_xsendfile or similar functionality.
    Use django's static serve option for development servers"""

    original_path = full_path
    archived_path = re.sub(ARCHIVE_RE, ARCHIVE_DIR, original_path)

    file_path = original_path if os.path.exists(original_path) else archived_path
    if not os.path.exists(file_path):
        logger.warning("Path not found: {}".format(file_path))
        return http.HttpResponseNotFound()

    if FRONTEND == "xsendfile":
        response = HttpResponse()
        response['X-Sendfile'] = file_path
        if attachment:
            response['Content-Disposition'] = 'attachment; filename=%s' % os.path.basename(file_path)

        # Unset the Content-Type as to allow for the webserver
        # to determine it.
        response['Content-Type'] = ''

    elif FRONTEND == "xaccelredirect":
        response = HttpResponse()
        response['X-Accel-Redirect'] = file_path

        if attachment:
            response['Content-Disposition'] = 'attachment; filename=%s' % os.path.basename(file_path)
        response['Content-Type'] = ''

    else:
        dirname = os.path.dirname(file_path)
        path = os.path.basename(file_path)

        # "Serving file %s in directory %s through django static serve." % (path, dirname)
        response = serve(request, path, dirname)

    return response


def send_snapshot(request, key, path):
    directory = get_download_path(key)
    if not os.path.exists(directory):
        directory = re.sub(ARCHIVE_RE, ARCHIVE_DIR, directory)
    if os.path.exists(directory):
        filename = os.path.join(CACHE_DIR, key, path)
        original_file = os.path.join(directory, path)
        name, ext = os.path.splitext(path)
        pngs = glob.glob(os.path.join(directory, '{}_*.png'.format(name)))
        if ext.lower() == '.gif' and os.path.exists(filename):
            return send_raw_file(request, filename, attachment=False)
        elif ext == '.png' and os.path.exists(original_file):
            return send_raw_file(request, original_file)
        elif len(pngs) == 1:
            return send_raw_file(request, pngs[0], attachment=False)
        elif pngs:
            create_cache_dir(key)
            command = 'convert -delay 200 -resize 500x {0} {1}'.format(' '.join(pngs), filename)
            try:
                subprocess.check_call(command.split())
            except subprocess.CalledProcessError:
                return http.HttpResponseNotFound()
            return send_raw_file(request, filename, attachment=False)
    return send_raw_file(request, utils.get_missing_snapshot())


def send_frame(request, key, path, brightness):
    directory = get_download_path(key)
    if not os.path.exists(directory):
        directory = re.sub(ARCHIVE_RE, ARCHIVE_DIR, directory)
    if os.path.exists(directory):
        cache_path = os.path.splitext(path)[0]
        frame_image = os.path.join(CACHE_DIR, key, cache_path, '{}.png'.format(brightness))
        frame_file = os.path.join(directory, path)
        if os.path.exists(frame_image):
            return send_raw_file(request, frame_image, attachment=False)
        elif os.path.exists(frame_file):
            target_dir = os.path.dirname(frame_image)
            if not os.path.exists(target_dir):
                os.makedirs(target_dir)
            utils.create_png(frame_file, frame_image, BRIGHTNESS.get(brightness, 0.0))
            return send_raw_file(request, frame_image)
    return send_raw_file(request, utils.get_missing_frame())


def send_file(request, key, path):

    document_root = get_download_path(key)

    # Clean up given path to only allow serving files below document_root.
    path = posixpath.normpath(urllib.unquote(path))
    drive, path = os.path.splitdrive(path)  # Remove drive in case path is absolute
    path = path.lstrip(os.path.sep)
    full_path = os.path.normpath(os.path.join(document_root, path))

    if not full_path.startswith(document_root):
        return http.HttpResponseNotFound()

    if os.path.exists('{}.gz'.format(full_path)):
        return send_uncompressed_file(request, key, full_path)

    return send_raw_file(request, full_path)


def send_archive(request, key, path):  # Add base parameter and another url
    obj = get_object_or_404(SecurePath, key=key)
    target_path = obj.path.rstrip(os.sep)

    if len(target_path.split(os.sep)) < 4:
        return http.HttpResponseForbidden()

    archived_path = re.sub(ARCHIVE_RE, ARCHIVE_DIR, target_path)
    source_path = os.path.normpath(target_path if os.path.exists(target_path) else archived_path)

    if os.path.exists(source_path):
        p = subprocess.Popen(
            ['tar', '-czf', '-', os.path.basename(source_path)],
            cwd=os.path.dirname(source_path),
            stdout=subprocess.PIPE
        )

        response = StreamingHttpResponse(p.stdout, content_type='application/x-gzip')
        response['Content-Disposition'] = 'attachment; filename={}'.format(path)

        return response
    else:
        return http.HttpResponseNotFound()

