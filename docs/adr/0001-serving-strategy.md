# Serving strategy for downloads

We support multiple delivery backends for protected files: X-Sendfile, X-Accel-Redirect, and Django's static file serving for development. This keeps deployment flexible while preserving one application-level access path.

The default production runtime is a containerized Apache/httpd deployment. The image is assembled from `deploy/build-image.sh`, the process is started by `deploy/run-server.sh`, and the HTTP/WSGI configuration lives in `deploy/dataserver.conf`. Within that container, Apache owns the public HTTP surface and delegates the protected download endpoints to the Django app via WSGI, while the app still decides which backend to use for each file response.

This is the deployment-specific expression of the same decision: the app exposes one secure download contract, and the host runtime chooses the most suitable delivery mechanism for that environment without changing the product behavior.
