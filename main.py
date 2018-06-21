import sys
import http
import http.server
import socketserver
import requests


# script usage exaple:
# $ sudo python3 main.py BIND_ADDRESS BIND_PORT PROXY_ADDRESS
# $ sudo python3 main.py 10.189.121.133 80 http://user:pass@host:port


http_proxy = 'localhost:3128'


class ReqHandler(http.server.BaseHTTPRequestHandler, socketserver.ThreadingMixIn):
    def do_GET(self):
        # requests HTTP session
        sess = requests.Session()
        sess.proxies = {
            'http': http_proxy,
            'https': http_proxy,
        }

        url = 'https://releases.jolla.com' + self.path
        r = sess.get(url, stream=True)

        self.send_response(r.status_code, '')
        for h in r.headers:
            self.send_header(h[0], h[1])
        self.end_headers()
        for chunk in r.iter_content(chunk_size=128):
            self.wfile.write(chunk)


class ReleasesServer(http.server.HTTPServer):
    def __init__(self, server_address):
        self.bind_address = server_address
        super(ReleasesServer, self).__init__(server_address, ReqHandler)


def main():
    global http_proxy
    http_proxy = sys.argv[3]
    server_address = (sys.argv[1], int(sys.argv[2]))
    srv = ReleasesServer(server_address)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
