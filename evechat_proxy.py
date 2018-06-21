import sys
import selectors
import socket
import socketserver


# script usage exaple:
# $ python3 evechat_proxy.py
# $ python3 evechat_proxy.py

# Could not connect to chat server at tranquility.chat.eveonline.com:5222.
# Please ensure that this port isn't blocked.Retry?

class RedirectorServerHandler(socketserver.BaseRequestHandler):
    def setup(self):
        self.selector = selectors.DefaultSelector()
        try:
            # self.out_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
            self.out_socket = socket.create_connection(('tranquility.chat.eveonline.com', 5222), 0)
            self.selector.register(self.out_socket, selectors.EVENT_READ | selectors.EVENT_WRITE)
        except OSError as e:
            print(e)

    def handle(self):
        # print('handle(), request: ', type(self.request))
        # self.request is a client socket object
        print('handle new client: {}'.format(self.request.getpeername()))
        self.selector.register(self.request, selectors.EVENT_READ)
        try:
            while True:
                # ret = select.select([self.out_socket], None, None)
                # ret = self.selector.select(1)
                ret = self.selector.select()
                # print('selector ret', ret)
                for key, events_mask in ret:
                    ready_socket = key.fileobj
                    deststr = 'to chat'
                    if ready_socket == self.out_socket:
                        other_socket = self.request
                        deststr = 'to client'
                    else:
                        other_socket = self.out_socket
                    if events_mask & selectors.EVENT_READ:
                        buf = ready_socket.recv(4096)
                        other_socket.send(buf)
                        print('    resent {} bytes {}'.format(len(buf), deststr))
        except OSError as e:
            print(e)
        self.selector.unregister(self.out_socket)
        self.selector.unregister(self.request)


class RedirectorServer(socketserver.ThreadingTCPServer):
    def __init__(self, server_address):
        # self.bind_address = server_address
        # server_address is saved by parent class to self.server_address
        self.allow_reuse_address = True
        super(RedirectorServer, self).__init__(server_address, RedirectorServerHandler)


def main():
    # server_address = (sys.argv[1], int(sys.argv[2]))
    server_address = ('0.0.0.0', 5222)
    print('Will listen on', server_address)
    srv = RedirectorServer(server_address)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
