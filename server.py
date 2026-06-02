import http.server
import socketserver
import mimetypes
import os
import posixpath
from http.cookies import SimpleCookie

PORT = 8000

# Files for the no-route fallback are served from here.
ROOT = os.path.dirname(os.path.abspath(__file__))


class File:
    """Marker for a route body that should be loaded from a file on disk."""

    def __init__(self, path):
        self.path = path


# Define routes here: path -> (status, headers, body)
# body may be a string, or File("name.html") to load content from disk.
# To set cookies on a response, add them to the headers dict as a list:
#   "Set-Cookie": ["session=abc; Path=/; HttpOnly", "theme=dark"]
ROUTES = {
    "/": (
        200,
        {"Content-Type": "text/html", "Cache-Control": "no-store"},
        File("index.html"),
    ),
}


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        cookies = SimpleCookie(self.headers.get("Cookie"))
        request_cookies = {k: v.value for k, v in cookies.items()}

        route = ROUTES.get(self.path)
        if route is None:
            # No route: try to serve a file matching the request path.
            route = self.file_route(self.path, request_cookies)
        if route is None:
            self.send_error(404, "Not Found")
            return
        status, headers, body = route

        # A File body is loaded from disk; everything else is inline text.
        if isinstance(body, File):
            with open(body.path, "rb") as f:
                body = f.read()
        else:
            body = body.encode()
        self.send_response(status)
        for name, value in headers.items():
            # A header value can be a list (e.g. multiple Set-Cookie headers)
            for v in value if isinstance(value, list) else [value]:
                self.send_header(name, v)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def file_route(self, path, request_cookies):
        rel = posixpath.normpath(path).lstrip("/")
        full = os.path.abspath(os.path.join(ROOT, rel))
        if not full.startswith(ROOT) or not os.path.isfile(full):
            return None
        # If a cookie named after the requested file is set, serve the
        # alternate "name.alt.ext" version instead (when it exists).
        if os.path.basename(full) in request_cookies:
            stem, ext = os.path.splitext(full)
            alt = stem + ".alt" + ext
            if os.path.isfile(alt):
                full = alt
        ctype = mimetypes.guess_type(full)[0] or "application/octet-stream"
        return (200, {"Content-Type": ctype, "Cache-Control": "no-store"}, File(full))


class Server(socketserver.TCPServer):
    # Let the port be rebound immediately instead of waiting out TIME_WAIT.
    allow_reuse_address = True


with Server(("", PORT), Handler) as httpd:
    print("serving at port", PORT)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nshutting down")
