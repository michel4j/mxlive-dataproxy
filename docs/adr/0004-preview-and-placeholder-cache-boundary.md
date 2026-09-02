# Preview and placeholder cache boundary

- Status: Accepted

## Context

The proxy serves raw files, generated frame previews, and snapshot alternatives. Rendering previews from source files on the fly is expensive and couples request latency to image conversion, but the source directories must remain isolated from cache artifacts.

At the same time, clients still need a consistent response when a requested preview or snapshot is absent. A missing source should not surface as a raw filesystem error; it should resolve to a defined placeholder asset.

## Decision

We keep generated previews and fallback placeholders in a dedicated cache directory (`DOWNLOAD_CACHE_DIR`) while leaving the original files in the registered download paths. `SendFrame` first checks whether a PNG already exists in cache; if not, it renders one from the underlying file and stores it in the keyed cache location. `send_snapshot` follows the same pattern for alternate snapshot extensions, then falls back to the missing-snapshot placeholder when nothing matches.

The placeholder asset is treated as a stable generated resource rather than a source file. That makes the UI contract predictable: a missing frame or snapshot still resolves to an image response, but the backing storage path remains hidden from the client.

## Consequences

- Render cost is amortized across requests through a cache that is explicitly separated from the protected source data.
- The proxy keeps a clear boundary between source files and derived assets, which makes access control and cleanup easier to reason about.
- Missing resources degrade gracefully to a placeholder response instead of exposing raw 404 behavior or leaking directory structure.
- The cache directory becomes part of the runtime contract of the proxy and should be treated as a managed artifact, not as a user-provided path.
