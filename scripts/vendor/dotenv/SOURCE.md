# Vendored python-dotenv parser

- Upstream: https://github.com/theskumar/python-dotenv
- Version: v1.2.1, commit `eaf2a9129ccec6febda0f741eb3bb852c3f947bd`
- Files: `src/dotenv/parser.py` and `LICENSE`, unchanged.
- Use: `scripts/deployment.py` reads only `CONTAINER_ENGINE` from the root `.env`
  with `parse_stream()`. It does not export or interpolate any value.
- Removal: delete this directory and the import in `scripts/deployment.py` if the
  engine selector moves out of `.env`.
