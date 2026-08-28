# MXLive Data Proxy

This context covers the project-wide vocabulary for protected file downloads, generated previews, and archive delivery.

## Language

**Download Key**:
A token that identifies a registered download path and authorizes access to it.
_Avoid_: SecurePath, download grant

**Download Path**:
A path registered for protected access through a download key.
_Avoid_: Secure path, source path

**Frame**:
A rendered image preview generated from frame data.
_Avoid_: Preview, image render

**Snapshot**:
A stored image file served directly as an alternate representation of a download.
_Avoid_: Thumbnail, preview image

**Archive**:
A tar.gz download of a registered directory.
_Avoid_: Bundle, compressed download
