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
            print('Connecting to chat server... ', end='')
            # self.out_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
            self.out_socket = socket.create_connection(('tranquility.chat.eveonline.com', 5222), 20)
            self.selector.register(self.out_socket, selectors.EVENT_READ | selectors.EVENT_WRITE)
            print('Connected.')
        except OSError as e:
            print(e)

    def handle(self):
        # print('handle(), request: ', type(self.request))
        # self.request is a client socket object
        self.client_address = self.request.getpeername()
        print('handle new client: {}'.format(self.request.getpeername()))
        self.selector.register(self.request, selectors.EVENT_READ)
        bytes_total = 0
        current_mb = 0
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
                        # debug
                        sbuf = buf.decode('utf-8')
                        print(sbuf)
                        # stats
                        bytes_total += len(buf)
                        current_mb += len(buf)
                        if current_mb > 1024 * 1024:  # report data size every 1 Mb
                            mbs_sent = bytes_total / 1024 / 1024
                            print('    Client {}: MBytes sent: {}'.format(self.client_address, mbs_sent))
                            current_mb = 0
        except OSError as e:
            print(e)
        # close all proxy sockets
        try:
            self.selector.unregister(self.out_socket)
            self.selector.unregister(self.request)
            self.request.shutdown(socket.SHUT_WR)
            self.request.close()
            self.out_socket.shutdown(socket.SHUT_WR)
            self.out_socket.close()
        except OSError:
            pass
        print('Client finished: {}, bytes sent: {}'.format(self.client_address, bytes_total))


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
