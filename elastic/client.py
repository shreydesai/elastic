import socket
import select
import sys

import settings

class Client:

    def __init__(self):
        self.input_sockets = []
        self.server_sock = self._connect()

        self.input_sockets.append(sys.stdin)
        self.input_sockets.append(self.server_sock)

    def _connect(self):
        server_address = (settings.SERVER_IP_ADDRESS, settings.SERVER_PORT)
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        server.connect(server_address)
        print('Client connected to {}:{}'.format(*server_address))

        return server

    def _handle_response(self, sock, data):
        if data:
            msg = data.decode(settings.ENCODING)
            if len(msg) == 0:
                print('Server disconnected')
                sys.exit(1)
            if msg != settings.ACK:
                print(msg)
        else:
            print('Server disconnected')
            sys.exit(1)
            
    def _send_request(self, sock):
        msg = sys.stdin.readline()
        encoded_msg = msg.encode(settings.ENCODING)
        sock.send(encoded_msg)

    def start(self):
        while True:
            readable, _, _ = select.select(self.input_sockets, [], [])
            for input_sock in readable:
                if input_sock is self.server_sock:
                    data = input_sock.recv(settings.BUFFER_SIZE)
                    self._handle_response(input_sock, data)
                else:
                    self._send_request(self.server_sock)


if __name__ == '__main__':
    client = Client()
    client.start()
