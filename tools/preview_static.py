"""Local static preview with explicit SVG MIME, independent of Windows registry."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer


class PreviewHandler(SimpleHTTPRequestHandler):
    extensions_map = {**SimpleHTTPRequestHandler.extensions_map, ".svg": "image/svg+xml"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", default=".output/public")
    parser.add_argument("--port", type=int, default=4175)
    arguments = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", arguments.port), partial(PreviewHandler, directory=arguments.directory))
    print(f"Preview: http://127.0.0.1:{arguments.port}", flush=True)
    server.serve_forever()
