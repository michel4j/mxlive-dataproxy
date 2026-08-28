# Serving strategy for downloads

We support multiple delivery backends for protected files: X-Sendfile, X-Accel-Redirect, and Django's static file serving for development. This keeps deployment flexible while preserving one application-level access path.
