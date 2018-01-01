import socket
import select

from elastic import settings

class Server:

    def __init__(self):
        self.input_sockets = []
        self.exceptional_sockets = []
        self.client_sockets = []
        self.server_sock = self._connect()

        self.input_sockets.append(self.server_sock)

    def _connect(self):
        server_address = (settings.SERVER_IP_ADDRESS, settings.SERVER_PORT)
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.setblocking(0)

        server.bind(server_address)
        server.listen(5)

        print('Server started on {}:{}'.format(*server_address))

        return server

    def _handle_request(self, client_sock, data):
        if data:
            print('Received {} from {}:{}'.format(
                data, *client_sock.getpeername()
            ))
            self._broadcast(client_sock, data)
        else:
            self._disconnect_client(client_sock)

    def _broadcast(self, client_sock, data):
        for sock in self.client_sockets:
            if sock is client_sock:
                msg = settings.ACK
                encoded_msg = msg.encode(settings.ENCODING)
                sock.send(encoded_msg)
            else:
                msg = data.decode(settings.ENCODING).strip()
                fmt_msg = '[{}:{}] {}'.format(*client_sock.getpeername(), msg)
                encoded_msg = fmt_msg.encode(settings.ENCODING)
                sock.send(encoded_msg)

    def _register_client(self, client_sock):
        self.input_sockets.append(client_sock)
        self.client_sockets.append(client_sock)
        print('Client {}:{} connected'.format(
            *client_sock.getsockname()
        ))
        msg = settings.ACK
        encoded_msg = msg.encode(settings.ENCODING)
        client_sock.send(encoded_msg)

    def _disconnect_client(self, client_sock):
        print('Client {}:{} has disconnected'.format(
            *client_sock.getsockname()
        ))
        self.input_sockets.remove(client_sock)
        self.client_sockets.remove(client_sock)
        client_sock.close()

    def start(self):
        while self.input_sockets:
            readable, writable, exceptional = \
                select.select(self.input_sockets, [], self.exceptional_sockets)

            for read_sock in readable:
                if read_sock is self.server_sock:
                    client_sock, client_addr = read_sock.accept()
                    client_sock.setblocking(0)
                    self._register_client(client_sock)
                else:
                    data = read_sock.recv(settings.BUFFER_SIZE)
                    self._handle_request(read_sock, data)

            for exceptional_sock in exceptional:
                exceptional_sock.close()
                self.input_socks.remove(sock)

if __name__ == '__main__':
    server = Server()
    server.start()
