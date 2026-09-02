# MXLive Data Proxy

This context covers the project-wide vocabulary and architecture for protected file downloads, generated previews, and archive delivery.

## System overview

The data proxy sits in front of storage and exposes a protected, key-based access layer for MxLIVE. It does not hand out raw filesystem paths to callers. Instead, it stores a registry of approved download paths, returns an opaque key to authorized callers, and resolves that key back to the file or directory the request needs.

The service enforces four behavioral boundaries:

- Only directories present in `DOWNLOAD_DIRS` can be registered for protected access.
- The registry stores a path and a generated key in the database, not the caller-facing location itself.
- Normalized request paths may be resolved under a user root and substitute directories before the file is served.
- Generated preview assets are stored under a separate cache directory so the source data remains isolated from runtime rendering.

## Deployment model

The application is packaged as a container image built by `deploy/build-image.sh` and launched by `deploy/run-server.sh`. The runtime image starts Apache httpd with a WSGI mount for the Django app, and the container-level configuration lives in `deploy/dataserver.conf`.

This means the data proxy is not a standalone Django development server in production: it is a containerized Apache/WSGI deployment that exposes the same request flow inside a managed runtime. The reverse proxy or hosting environment is expected to route traffic to the container, while the app itself enforces the key-based access layer for download requests.

## Validation and rollout for container updates

The Python 3.14 slim migration is a packaging change, not a product change, so the rollout gate is operational rather than feature-level. A release should only proceed after the rebuilt image passes a minimal smoke-test sequence that exercises the same runtime contract as production.

1. Build validation: rebuild the image with the project’s normal `deploy/build-image.sh` path and verify the final image uses the supported Python base without leftover compiler or package-manager artifacts.
2. Runtime startup validation: start the container and confirm `deploy/run-server.sh` still initializes database migrations, creates the required local runtime directories, and launches Apache in the foreground without crashing.
3. Apache and WSGI validation: check that `deploy/dataserver.conf` loads cleanly, that the `XSendFilePath` entries still include `/users`, `/archive`, and `/cache`, and that the WSGI mount serves the Django app instead of failing during import.
4. Secure-download validation: POST to `/data/create/` with a configured path, confirm the response contains a 40-character key, and then request the protected file route using that key to verify the file-serving flow still resolves and returns the expected response headers.
5. Placeholder and cache validation: request a missing frame or snapshot and confirm the operation falls back to a placeholder rather than exposing a raw filesystem error.
6. Canary rollout: deploy the rebuilt image to a staging or single-host slot first, keep the previous image available for rollback, and watch Apache logs for WSGI import failures, X-Sendfile path errors, or missing runtime directories.

This keeps the migration narrow and safe: the application behavior remains the same, while the container packaging and runtime assumptions are validated before broad rollout.

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
