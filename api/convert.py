import json
import os
import tempfile
from http.server import BaseHTTPRequestHandler
import cgi


class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        self.send_response(200)
        self._set_cors()
        self.end_headers()

    def do_POST(self):
        try:
            from markitdown import MarkItDown
        except ImportError:
            self._error(500, "markitdown not installed")
            return

        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type:
            self._error(400, "Expected multipart/form-data")
            return

        try:
            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={
                    "REQUEST_METHOD": "POST",
                    "CONTENT_TYPE": content_type,
                }
            )
        except Exception as e:
            self._error(400, f"Failed to parse form: {e}")
            return

        if "file" not in form:
            self._error(400, "No file field in form")
            return

        file_item = form["file"]
        filename = file_item.filename or "upload"
        file_data = file_item.file.read()

        ext = os.path.splitext(filename)[-1].lower() or ".bin"
        suffix = ext if ext else ".bin"

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(file_data)
            tmp_path = tmp.name

        try:
            md = MarkItDown()
            result = md.convert(tmp_path)
            content = result.text_content
            self._json({"filename": filename, "content": content, "engine": "markitdown"})
        except Exception as e:
            self._error(500, f"Conversion failed: {e}")
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    def _json(self, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._set_cors()
        self.end_headers()
        self.wfile.write(body)

    def _error(self, code, msg):
        body = json.dumps({"error": msg}).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._set_cors()
        self.end_headers()
        self.wfile.write(body)

    def _set_cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
