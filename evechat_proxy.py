import sys
import selectors
import socket
import socketserver


# script usage exaple:
# $ python3 evechat_proxy.py
# $ python3 evechat_proxy.py

# Could not connect to chat server at tranquility.chat.eveonline.com:5222.
# Please ensure that this port isn't blocked.Retry?
# Newer address: tq.chat.eveonline.com:5222

g_num_threads = 0


class RedirectorServerHandler(socketserver.BaseRequestHandler):
    def setup(self):
        self.selector = selectors.DefaultSelector()
        try:
            print('RedirectorServerHandler.setup: Connecting to chat server... ', end='', file=sys.stderr)
            # self.out_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
            # self.out_socket = socket.create_connection(('tranquility.chat.eveonline.com', 5222), 20)
            self.out_socket = socket.create_connection(('tq.chat.eveonline.com', 5222), 20)
            self.selector.register(self.out_socket, selectors.EVENT_READ)
            print('Connected.')
        except OSError as e:
            print('OSError: {}'.format(e), file=sys.stderr)
            print('RedirectorServerHandler.setup: got OSError ^^', file=sys.stderr)

    def handle(self):
        # print('handle(), request: ', type(self.request))
        # self.request is a client socket object
        global g_num_threads
        g_num_threads += 1
        my_thread_num = g_num_threads
        self.client_address = self.request.getpeername()
        print('{} RedirectorServerHandler.handle: new client: {}'.format(
            my_thread_num, self.request.getpeername()),
            file=sys.stderr)
        self.request.settimeout(None)  # blocking mode
        # self.request.settimeout(15)  # 15s
        self.selector.register(self.request, selectors.EVENT_READ)
        bytes_total = 0
        current_mb = 0
        try:
            while True:
                # ret = select.select([self.out_socket], None, None)
                ret = self.selector.select(1)
                # print('    selector ret', ret)
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
                        # sbuf = buf.decode('utf-8')
                        # print(buf) # actually data is encrypted using TLS
                        #   (StartTLS jabber extension.)
                        # stats
                        bytes_total += len(buf)
                        current_mb += len(buf)
                        if current_mb > 1024 * 1024:  # report data size every 1 Mb
                            mbs_sent = bytes_total / 1024 / 1024
                            print('   {} Client {}: MBytes sent: {}'.format(
                                my_thread_num, self.client_address, mbs_sent),
                                file=sys.stderr)
                            current_mb = 0
        except OSError as e:
            print('{} RedirectorServerHandler.handle: OSError: {}'.format(my_thread_num, e),
                  file=sys.stderr)
        # close all proxy sockets
        try:
            self.selector.unregister(self.out_socket)
            self.selector.unregister(self.request)
            self.request.shutdown(socket.SHUT_RDWR)
            self.request.close()
            self.out_socket.shutdown(socket.SHUT_RDWR)
            self.out_socket.close()
        except OSError:
            pass
        print('{} RedirectorServerHandler.handle: Client finished: {}, bytes sent: {}'.format(
            my_thread_num, self.client_address, bytes_total),
            file=sys.stderr)
        g_num_threads -= 1


class RedirectorServer(socketserver.ThreadingTCPServer):
    def __init__(self, server_address):
        # self.bind_address = server_address
        # server_address is saved by parent class to self.server_address
        self.allow_reuse_address = True
        super(RedirectorServer, self).__init__(server_address, RedirectorServerHandler)


def main():
    # server_address = (sys.argv[1], int(sys.argv[2]))
    server_address = ('0.0.0.0', 5222)
    print('Will listen on: ', server_address, file=sys.stderr)
    srv = RedirectorServer(server_address)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
