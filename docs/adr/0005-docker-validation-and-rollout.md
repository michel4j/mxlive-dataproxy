# Docker validation and rollout plan

- Status: Accepted

## Context

The application is deployed as a containerized Apache/WSGI service that starts through `deploy/run-server.sh` and is configured via `deploy/dataserver.conf`. The current migration work moves the image from a Fedora-based runtime to the official `python:3.14-slim` base, while preserving the same secure-download contract and Apache access model.

This is a packaging change with operational risk. The app logic itself is stable, but the runtime has several sensitive assumptions: Apache must start in the foreground, mod_wsgi must import the Django app, the secure file hooks must still resolve paths under `/users`, `/archive`, and `/cache`, and generated previews must remain isolated from the protected storage roots.

## Decision

We treat the container migration as a release with a validation gate rather than a blind rebuild. The image is considered releasable only after it passes the following checks in a fresh container:

1. Build verification: the image is created from the standard deployment script and does not retain compiler chains or package-manager caches in the final runtime.
2. Startup verification: `deploy/run-server.sh` runs successfully, creates the required local state, and starts Apache in the foreground with no crash loop.
3. Config verification: `deploy/dataserver.conf` is copied into the runtime and still loads cleanly with the expected `XSendFilePath` values and WSGI mount for `/dataserver/dataserver/wsgi.py`.
4. Request-path verification: a real protected file flow is exercised by creating a secure key through `/data/create/`, then fetching the resulting raw or snapshot route to confirm the response is still served through the configured delivery path.
5. Placeholder/cache verification: a missing frame or snapshot still resolves to the configured placeholder asset rather than exposing a raw path failure.
6. Rollout verification: the upgraded image is deployed to staging or a single canary instance first, with the old image retained as rollback, and logs are checked for WSGI startup problems, X-Sendfile path failures, or database bootstrap issues.

The validation sequence is intentionally compact: it checks the exact runtime boundaries that matter for this app, not unrelated application behavior.

## Consequences

- The migration remains narrow and reversible: a failed runtime check can be rolled back to the previous image without a code revert.
- The secure-download contract remains the release gate, because the app is only valid if the container still serves protected files and placeholders correctly.
- Operational logging and startup checks become part of the deployment discipline for the Python 3.14 change, which reduces the chance of a silent runtime regression.
- The final image remains focused on the runtime contract instead of carrying unnecessary package-manager or build artifacts.
