import html
import json
import os
import secrets
import socket
from http import cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

APP_VERSION = "1.4.2"
DATABASE_URL = os.environ.get("DATABASE_URL", "postgres://enigma:enigma@db:5432/enigma")

todos = []
sessions = {}

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%s · enigma</title>
<style>
 body { font-family: system-ui, sans-serif; background: #f4f4f5; margin: 0; display: grid; place-items: center; min-height: 100vh; }
 main { background: #fff; padding: 2rem; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,.1); width: 22rem; }
 h1 { font-size: 1.25rem; margin-top: 0; }
 input[type=text], input[type=password] { width: 100%%; box-sizing: border-box; padding: .5rem; margin: .25rem 0 .75rem; border: 1px solid #d4d4d8; border-radius: 4px; }
 button { padding: .5rem 1rem; border: 0; border-radius: 4px; background: #18181b; color: #fff; cursor: pointer; }
 ul { list-style: none; padding: 0; }
 li { display: flex; justify-content: space-between; align-items: center; gap: .5rem; padding: .4rem 0; border-bottom: 1px solid #e4e4e7; }
 li form { margin: 0; }
 li button { background: none; color: #a1a1aa; padding: .1rem .4rem; }
 nav { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 1rem; }
 nav a { color: #71717a; font-size: .8rem; }
 .muted { color: #71717a; font-size: .8rem; }
</style>
</head>
<body><main>%s</main></body>
</html>"""


def database_reachable():
    parsed = urlparse(DATABASE_URL)
    try:
        with socket.create_connection((parsed.hostname, parsed.port or 5432), timeout=2):
            return True
    except OSError:
        return False


class Handler(BaseHTTPRequestHandler):
    server_version = f"enigma/{APP_VERSION}"

    def current_user(self):
        jar = cookies.SimpleCookie(self.headers.get("Cookie"))
        morsel = jar.get("session")
        return sessions.get(morsel.value) if morsel else None

    def send_html(self, body, title="enigma", status=200, extra_headers=None):
        page = (PAGE % (title, body)).encode()
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(page)))
        for name, value in (extra_headers or []):
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(page)

    def send_json(self, status, payload):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def redirect(self, location, extra_headers=None):
        self.send_response(303)
        self.send_header("Location", location)
        for name, value in (extra_headers or []):
            self.send_header(name, value)
        self.end_headers()

    def read_form(self):
        length = min(int(self.headers.get("Content-Length", 0)), 65536)
        return parse_qs(self.rfile.read(length).decode())

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/health":
            return self.health()
        if path == "/":
            return self.redirect("/todos" if self.current_user() else "/login")
        if path == "/login":
            if self.current_user():
                return self.redirect("/todos")
            return self.send_html(LOGIN_BODY, "sign in")
        if path == "/logout":
            jar = cookies.SimpleCookie(self.headers.get("Cookie"))
            morsel = jar.get("session")
            if morsel:
                sessions.pop(morsel.value, None)
            return self.redirect("/login", [("Set-Cookie", "session=; Max-Age=0; Path=/; HttpOnly")])
        if path == "/todos":
            user = self.current_user()
            if not user:
                return self.redirect("/login")
            return self.send_html(todos_body(user), "todos")
        self.send_json(404, {"error": "not found"})

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/login":
            form = self.read_form()
            username = form.get("username", [""])[0].strip()[:64]
            if not username or not form.get("password", [""])[0]:
                return self.send_html(LOGIN_BODY + '<p class="muted">Username and password required.</p>', "sign in", 400)
            token = secrets.token_hex(16)
            sessions[token] = username
            return self.redirect("/todos", [("Set-Cookie", f"session={token}; Path=/; HttpOnly; SameSite=Lax")])
        if path == "/todos":
            if not self.current_user():
                return self.redirect("/login")
            title = self.read_form().get("title", [""])[0].strip()[:200]
            if title:
                todos.append(title)
            return self.redirect("/todos")
        if path == "/todos/delete":
            if not self.current_user():
                return self.redirect("/login")
            try:
                del todos[int(self.read_form().get("index", [""])[0])]
            except (ValueError, IndexError):
                pass
            return self.redirect("/todos")
        self.send_json(404, {"error": "not found"})

    def health(self):
        db = urlparse(DATABASE_URL)
        if database_reachable():
            return self.send_json(200, {"status": "ok", "storage": "postgres", "version": APP_VERSION})
        self.send_json(503, {
            "status": "unhealthy",
            "error": f"cannot connect to database at {db.hostname}:{db.port or 5432}",
            "storage": "in-memory (degraded)",
            "runbook": "DEBUGGING.md",
            "version": APP_VERSION,
        })


LOGIN_BODY = """
<h1>Sign in to enigma</h1>
<form method="post" action="/login">
  <label>Username<br><input type="text" name="username" autofocus></label><br>
  <label>Password<br><input type="password" name="password"></label><br>
  <button type="submit">Sign in</button>
</form>
"""


def todos_body(user):
    items = "".join(
        f'<li><span>{html.escape(title)}</span>'
        f'<form method="post" action="/todos/delete">'
        f'<input type="hidden" name="index" value="{index}">'
        f'<button type="submit" title="delete">✕</button></form></li>'
        for index, title in enumerate(todos)
    ) or '<li class="muted">Nothing here yet.</li>'
    return f"""
<nav><strong>enigma</strong><span>{html.escape(user)} · <a href="/logout">sign out</a></span></nav>
<h1>Todos</h1>
<ul>{items}</ul>
<form method="post" action="/todos">
  <input type="text" name="title" placeholder="Add a todo…" autofocus>
  <button type="submit">Add</button>
</form>
"""


if __name__ == "__main__":
    print(f"enigma {APP_VERSION} listening on :8080", flush=True)
    if database_reachable():
        print("storage: postgres", flush=True)
    else:
        print("WARNING: database unreachable - starting in degraded mode (in-memory storage)", flush=True)
        print("hint: follow the degraded-mode runbook in DEBUGGING.md", flush=True)
    ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
