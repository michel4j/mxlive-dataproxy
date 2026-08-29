# MXLive Data Proxy

Secure, key-based access to protected data and generated previews for MxLIVE.

## Overview

The data proxy sits in front of approved storage locations and exposes only opaque download keys to callers. It does not expose raw filesystem paths to the client; instead, it registers a protected path, returns a generated key, and resolves that key back to the actual file or directory when serving requests.

The service is designed around a few core properties:

- Allowlisted download roots only.
- Opaque keys instead of direct path disclosure.
- A clear boundary between source data and generated preview/cache artifacts.
- Apache + WSGI as the production serving layer in the container runtime.

## Deployment model

This project is not intended to run as a standalone Django dev server in production. The container image is built by `deploy/build-image.sh`, the service is started by `deploy/run-server.sh`, and Apache is configured via `deploy/dataserver.conf`.

At runtime, Apache serves the Django app through WSGI and uses the configured frontend strategy (`X-Sendfile`, `X-Accel-Redirect`, or Django static serving) to provide controlled file delivery.

## Architecture at a glance

1. A caller asks to create a protected path.
2. The path is normalized and checked against the configured download roots.
3. A `SecurePath` record is created with an opaque key.
4. Later requests resolve the key back to the backing file or directory.
5. Raw files, snapshot images, archive downloads, and generated frame previews are served through the protected flow.
6. Missing preview or snapshot content falls back to a placeholder instead of leaking filesystem details.

## Local development

For a local Django environment:

1. Copy the example settings if needed and adjust values for your environment.
2. Run migrations:

   ```bash
   ./manage.py migrate
   ```

3. Start the service:

   ```bash
   ./manage.py runserver 
   ```

4. Point the consuming MxLIVE configuration at `http://localhost:8000`.

## Container build and deployment

Build the image from the project directory:

```bash
./deploy/build-image.sh
```

An example `container-compose.yml` file is provided. Adapt it accordingly.
When integrating into a larger MxLIVE deployment:

1. Place your `settings.py` file in a separate local folder mapped to the local volume.
2. Ensure the required log directory exists.
3. Mount the data directories the proxy needs to access.
4. Restart the deployment so the new service definition is active.

## Project documentation

This repo includes architecture and decision records describing the design decisions behind the secure-download flow and deployment model:

- `CONTEXT.md` — shared vocabulary and system overview
- `docs/adr/0001-serving-strategy.md` — serving model and deployment choice
- `docs/adr/0003-secure-path-registry.md` — allowlist + opaque key design
- `docs/adr/0004-preview-and-placeholder-cache-boundary.md` — cache and preview boundaries
- `docs/adr/0005-docker-validation-and-rollout.md` — release validation and canary rollout guidance

## Security note

This service intentionally does not expose raw storage paths to requesters. All protected access is mediated by key lookup, path validation, and deployment-defined allowlists.


## Testing

To test the service on a directory of diffraction images `/data/test`, containing CBF files `frame_001.cbf ... frame_nnn.cbf` for example,
create a Download Key using the API as follows:

```bash
curl -i -H "Content-Type: application/json" -d '{"path":"/data/test"}' http://localhost:8000/download/data/create/
```
The POST request should return a key similar to `5bb2e3a426795b48adbc1584e97a720f3d36e16b`. You can then use the
key to access data from the directory as follows:

```bash
wget http://localhost:8000/download/files/frame/5bb2e3a426795b48adbc1584e97a720f3d36e16b/frame_001.cbf/nm.png
```

Fetches a PNG image of the diffraction with normal rendering. Use:

- `nm` - Normal rendering
- `dk` - Dark rendering
- `lt` - Light rendering
- `xl` - Extra-light rendering