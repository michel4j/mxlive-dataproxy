# Secure path registry and opaque keys

- Status: Accepted

## Context

The proxy needs to give MxLIVE access to files without exposing the underlying storage location. The system also needs to support tenant-specific directories and protect against arbitrary path traversal while working with a small configuration surface.

The implementation already relies on an allowlist of approved directories, a configured user-root prefix, and a database-backed path registry. Without a single explicit decision, future changes could drift into a more permissive model that leaks storage layout.

## Decision

We register each approved download path in a `SecurePath` record and generate an opaque 40-character key for it. The public API never exposes the backing path directly; instead it returns the key and looks up the path through the database later.

`CreatePath` accepts paths under `DOWNLOAD_DIRS`, normalizes relative paths against `LDAP_USER_ROOT`, and refuses any path outside the approved roots. The key itself is generated from the raw path plus a UUID salt using RIPEMD-160, which keeps the token opaque while still being compact and deterministic enough to be used in URLs.

## Consequences

- The real filesystem layout remains hidden behind the registry and the key token.
- Only approved directories can be registered, which keeps access control aligned with deployment configuration.
- Relative paths can be resolved consistently for tenant or user-specific roots without exposing a global file tree.
- The access model remains simple to reason about: if the key exists and resolves within the allowlist, serving is permitted; otherwise the request fails.
