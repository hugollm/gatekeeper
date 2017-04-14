from .requests.request import Request
from .responses.response import Response


class App(object):

    def __init__(self):
        self.endpoints = []
        self.paths = set()

    def endpoint(self, endpoint_class):
        endpoint = endpoint_class()
        if endpoint.path in self.paths:
            raise DuplicateEndpoints(endpoint.path)
        self.paths.add(endpoint.path)
        self.endpoints.append(endpoint_class())

    def __call__(self, env, start_response):
        request = Request(env)
        response = self.handle_request(request)
        return response.wsgi(start_response)

    def handle_request(self, request):
        response = self._try_to_get_response_from_an_endpoint(request)
        if response is None:
            response = self._response_404()
        return response

    def _try_to_get_response_from_an_endpoint(self, request):
        matched_endpoints = []
        for endpoint in self.endpoints:
            if endpoint.match_request(request):
                matched_endpoints.append(endpoint)
        if len(matched_endpoints) > 1:
            raise AmbiguousEndpoints(request.path)
        elif matched_endpoints:
            endpoint = matched_endpoints.pop()
            return endpoint.handle_request(request)
        return None

    def _response_404(self):
        response = Response()
        response.status = 404
        return response


class DuplicateEndpoints(Exception):

    def __init__(self, path):
        message = 'Cannot register two endpoints with the same path: ' + path
        super(DuplicateEndpoints, self).__init__(message)


class AmbiguousEndpoints(Exception):

    def __init__(self, path):
        message = 'The same path is leading to different endpoints: ' + path
        super(AmbiguousEndpoints, self).__init__(message)
