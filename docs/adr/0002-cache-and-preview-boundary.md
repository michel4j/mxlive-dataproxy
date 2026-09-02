# Cache and preview boundary

Generated frame previews live in a local cache directory, while source files remain under registered download paths. The split keeps expensive image rendering out of the hot path and makes the access boundary explicit.
