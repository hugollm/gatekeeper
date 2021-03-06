from datetime import datetime
from http.client import responses as STATUS_MESSAGES
from http.cookies import SimpleCookie
import mimetypes
import os

from ..exceptions import TemplateRendererNotSet
from ..case_insensitive_dict import CaseInsensitiveDict


class Response(BaseException):

    def __init__(self):
        self.status = 200
        self.headers = CaseInsensitiveDict({'Content-Type': 'text/plain; charset=utf-8'})
        self.cookies = []
        self._body = b''
        self._file = None
        self.template_renderer = None

    def __str__(self):
        return self.to_str()

    def __repr__(self):
        return self.to_str()

    def to_str(self):
        cls = type(self).__name__
        headers = len(self.headers)
        bytes = len(self._body)
        return '<{}:{}h:{}b>'.format(cls, headers, bytes)

    @property
    def body(self):
        return self._body

    @body.setter
    def body(self, value):
        if type(value) is not bytes:
            value = str(value).encode('utf-8')
        self._body = value

    def render(self, template_identifier, context=None):
        if self.template_renderer is None:
            raise TemplateRendererNotSet()
        self.body = self.template_renderer.render(template_identifier, context)
        return self

    def redirect(self, uri):
        self.status = 303
        self.headers['Location'] = uri
        return self

    def not_found(self):
        self.status = 404
        return self

    def bad_request(self):
        self.status = 400
        return self

    def unauthorized(self):
        self.status = 401
        return self

    def forbidden(self):
        self.status = 403
        return self

    def file(self, path, type=None, download=False, name=None):
        self._file = path
        if type is None:
            type, _ = mimetypes.guess_type(path)
        self.headers['Content-Type'] = type or 'application/octet-stream'
        self.headers['Content-Disposition'] = 'attachment' if download else 'inline'
        self.headers['Content-Disposition'] += '; filename="{}"'.format(name or os.path.basename(path))
        self.headers['Content-Length'] = str(os.stat(path).st_size)
        return self

    def set_cookie(self, key, value, expires=None, domain=None, path=None, secure=False, http_only=True, same_site=True):
        cookie = SimpleCookie({key: value}).get(key).OutputString()
        if expires:
            cookie += '; Expires=' + expires.strftime('%a, %d %b %Y %T') + ' GMT'
        if domain:
            cookie += '; Domain=' + domain
        if path:
            cookie += '; Path=' + path
        if secure:
            cookie += '; Secure'
        if http_only:
            cookie += '; HttpOnly'
        if same_site:
            cookie += '; SameSite=Strict'
        self.cookies.append(cookie)

    def unset_cookie(self, key, domain=None, path=None):
        cookie = key + '=; Expires=' + datetime(1970, 1, 1).strftime('%a, %d %b %Y %T') + ' GMT'
        if domain:
            cookie += '; Domain=' + domain
        if path:
            cookie += '; Path=' + path
        self.cookies.append(cookie)

    def wsgi(self, start_respose):
        start_respose(self._wsgi_status(), self._wsgi_headers())
        if self._file:
            return self._wsgi_file()
        return self._wsgi_body()

    def _wsgi_status(self):
        return str(self.status) + ' ' + STATUS_MESSAGES.get(self.status, '')

    def _wsgi_headers(self):
        headers = list(self.headers.items())
        for cookie in self.cookies:
            headers.append(('Set-Cookie', cookie))
        if 'Content-Length' not in self.headers:
            length = str(len(self.body))
            headers.append(('Content-Length', length))
        return headers

    def _wsgi_body(self):
        return (self.body,)

    def _wsgi_file(self):
        with open(self._file, 'rb') as f:
            mbyte = 1024 ** 2
            while True:
                chunk = f.read(mbyte)
                if not chunk:
                    break
                yield chunk
