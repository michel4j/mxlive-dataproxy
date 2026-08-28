# MXLive Data Proxy

This context covers the project-wide vocabulary and architecture for protected file downloads, generated previews, and archive delivery.

## System overview

The data proxy sits in front of storage and exposes a protected, key-based access layer for MxLIVE. It does not hand out raw filesystem paths to callers. Instead, it stores a registry of approved download paths, returns an opaque key to authorized callers, and resolves that key back to the file or directory the request needs.

The service enforces four behavioral boundaries:

- Only directories present in `DOWNLOAD_DIRS` can be registered for protected access.
- The registry stores a path and a generated key in the database, not the caller-facing location itself.
- Normalized request paths may be resolved under a user root and substitute directories before the file is served.
- Generated preview assets are stored under a separate cache directory so the source data remains isolated from runtime rendering.

## Core request flow

1. A caller requests a path through `CreatePath`.
2. The request is normalized to an absolute path under the configured user root when needed.
3. If the path is inside an approved directory, a `SecurePath` record is created and a 40-character key is returned.
4. Later requests resolve that key to the backing path and decide whether to serve raw content, a generated frame, a snapshot, or an archive.
5. If the source path or preview is missing, the proxy serves a placeholder instead of exposing a path failure.

## Domain vocabulary

**Download Key**:
A token that identifies a registered download path and authorizes access to it.
_Avoid_: SecurePath, download grant

**Download Path**:
A path registered for protected access through a download key.
_Avoid_: Secure path, source path

**SecurePath**:
The database record that binds a download path to its opaque key.
_Avoid_: Download grant, secure storage mapping

**Frame**:
A rendered image preview generated from frame data and cached under the configured preview cache.
_Avoid_: Preview, image render

**Snapshot**:
A stored image file served directly as an alternate representation of a download.
_Avoid_: Thumbnail, preview image

**Archive**:
A tar.gz download of a registered directory.
_Avoid_: Bundle, compressed download

**Cache boundary**:
The separation between source data under registered download paths and generated preview artifacts under `DOWNLOAD_CACHE_DIR`.
_Avoid_: Temporary storage, preview directory

**Frontend mode**:
The deployment-level response strategy for raw files (`X-Sendfile`, `X-Accel-Redirect`, or Django static serving).
_Avoid_: Transfer backend, download transport

## Architectural decisions to keep in mind

- The proxy is designed around an allowlist, not a generic file broker. Only configured directories may be exposed.
- Keys are opaque and deliberately not reused across paths; they are generated with a cryptographic hash plus a UUID salt.
- Paths are normalized before lookup to prevent accidental directory traversal and to support tenant-relative user roots.
- Generated previews and placeholder assets are treated as derived artifacts, not as source data; they live outside the protected storage roots.

## Security and delivery notes

- `send_file` resolves alternate paths and compressed variants before falling back to 404.
- `SendFrame` renders PNGs into the cache and serves the cached result on subsequent requests.
- `send_snapshot` probes common snapshot extensions and falls back to a missing snapshot placeholder when no image exists.
- `send_archive` streams tar.gz responses from the backing directory so callers receive a protected attachment without needing direct filesystem access.
