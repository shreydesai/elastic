import socket
import select
import pickle
import sys

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend

from elastic import settings
from elastic.message import ClientMessage, ServerMessage
from elastic.utils import generate_private_key, serialize_public_key

class Client:

    def __init__(self):
        self.input_sockets = []
        self.server_sock = self._connect()
        self.private_key = generate_private_key()
        self.public_key = self.private_key.public_key()
        self.server_public_key = None
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
            server_msg = pickle.loads(data)

            symmetric_key = self.private_key.decrypt(
                server_msg.symmetric_key,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA1()),
                    algorithm=hashes.SHA1(),
                    label=None
                )
            )

            f = Fernet(symmetric_key)
            msg_bytes = f.decrypt(server_msg.text)
            msg = msg_bytes.decode(settings.ENCODING)

            if len(msg) == 0:
                print('Server disconnected')
                sys.exit(1)
            if msg != settings.ACK:
                print(msg)
            print('>', end=' ', flush=True)
        else:
            print('Server disconnected')
            sys.exit(1)
            
    def _send_request(self, sock):
        msg = sys.stdin.readline()

        ciphertext = self.server_public_key.encrypt(
            msg.encode(settings.ENCODING),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA1()),
                algorithm=hashes.SHA1(),
                label=None
            )
        )
        client_msg = ClientMessage(ciphertext)
        encoded_msg = client_msg.serialize()

        sock.send(encoded_msg)

    def handshake(self):
        server_msg_bytes = self.server_sock.recv(settings.BUFFER_SIZE)
        server_msg = pickle.loads(server_msg_bytes)

        public_key_string = server_msg.text.strip()
        public_key = serialization.load_pem_public_key(
            public_key_string.encode(settings.ENCODING),
            default_backend()
        )
        self.server_public_key = public_key

        ciphertext = self.server_public_key.encrypt(
            'HANDSHAKE'.encode(settings.ENCODING),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA1()),
                algorithm=hashes.SHA1(),
                label=None
            )
        )
        client_msg = ClientMessage(
            ciphertext,
            serialize_public_key(self.public_key)
        )
        encoded_msg = client_msg.serialize()
        self.server_sock.send(encoded_msg)

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
    client.handshake()
    client.start()
