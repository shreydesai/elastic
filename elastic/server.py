import socket
import select
import pickle

from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend

from elastic import settings
from elastic.person import Person
from elastic.room import Room
from elastic.message import ClientMessage, ServerMessage
from elastic.utils import generate_private_key, serialize_public_key, \
                          encrypt_msg

class Server:

    def __init__(self, ip_address, port):
        self.ip_address = ip_address
        self.port = port
        self.input_sockets = []
        self.exceptional_sockets = []
        self.server_sock = self._connect()
        self.clients = {}
        self.rooms = {}
        self.private_key = generate_private_key()
        self.public_key = self.private_key.public_key()
        self.input_sockets.append(self.server_sock)

    def _connect(self):
        server_address = (self.ip_address, self.port)
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.setblocking(0)

        server.bind(server_address)
        server.listen(5)

        print('Server started on {}:{}'.format(*server_address))

        return server

    def _find_curr_room(self, person):
        for room in self.rooms.values():
            if room.search_client(person):
                return room
        return None

    def _handle_request(self, read_sock, data):
        person = self.clients[read_sock.getpeername()]

        if data:
            success = True
            client_msg = pickle.loads(data)

            plaintext = self.private_key.decrypt(
                client_msg.text,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA1()),
                    algorithm=hashes.SHA1(),
                    label=None
                )
            )
            msg = plaintext.decode(settings.ENCODING).strip()

            if not person.public_key:
                self._set_client_key(person, client_msg.public_key)

            print('Received {} bytes from {}:{}'.format(
                len(plaintext),
                *person.peer_addr()
            ))

            if msg.startswith('/help'):
                self._help(person)
            elif msg.startswith('/join'):
                success = self._join(person, msg)
            elif msg.startswith('/list'):
                self._list(person)
            else:
                curr_room = self._find_curr_room(person)
                if curr_room:
                    curr_room.broadcast(person, msg)
                else:
                    success = False

            if not success:
                self._help(person)
        else:
            self._disconnect_client(person)

    def _help(self, person):
        msg = '\nElastic Chat Server\n' + \
              '/help - Lists instructions.\n' + \
              '/join <name> <key> - Joins a room named <name>. If ' + \
              '<name> does not exist, then it will be created. <key> is ' + \
              'optional, but if specified, the room will be protected.\n' + \
              '/list - Lists all rooms.\n'
        encoded_msg = encrypt_msg(person, msg)
        person.send_msg(encoded_msg, encoded=True)

    def _join(self, person, msg):
        parts = msg.split(' ')
        _, name, key = (None,) * 3

        if len(parts) < 2:
            return False
        if len(parts) == 2:
            _, name = parts
        if len(parts) == 3:
            _, name, key = parts

        room = None
        curr_room = self._find_curr_room(person)
        name = name.strip()

        if name in self.rooms:
            room = self.rooms[name]
            if room.search_client(person):
                msg = 'You are already in room \'{}\'\n'.format(name)
                encoded_msg = encrypt_msg(person, msg)
                person.send_msg(encoded_msg, encoded=True)
                return True
        else:
            room = Room(name, person)
            if key:
                room.set_key(key)
            self.rooms[name] = room

        if room.is_protected():
            if key:
                if not room.correct_key(key):
                    msg = 'The key supplied was incorrect\n'
                    encoded_msg = encrypt_msg(person, msg)
                    person.send_msg(encoded_msg, encoded=True)
                    return True
            else:
                msg = 'This room requires a key to enter\n'
                encoded_msg = encrypt_msg(person, msg)
                person.send_msg(encoded_msg, encoded=True)
                return True

        if curr_room:
            curr_room.remove_client(person)
        room.add_client(person)

        return True

    def _list(self, person):
        string = ['Room\t\tClients']
        for name in sorted(self.rooms):
            room = self.rooms[name]
            string.append('{}{}\t\t{}'.format(
                '*' if room.is_protected() else '',
                room.name,
                len(room.clients)
            ))
        msg = '\n'.join(string) + '\n'
        encoded_msg = encrypt_msg(person, msg)
        person.send_msg(encoded_msg, encoded=True)

    def _set_client_key(self, person, public_key_string):
        print('Set public key for client {}:{}'.format(*person.peer_addr()))
        public_key = serialization.load_pem_public_key(
            public_key_string.encode(settings.ENCODING), default_backend()
        )
        person.public_key = public_key

    def _register_client(self, person):
        print('Client {}:{} connected'.format(*person.peer_addr()))
        self.input_sockets.append(person.sock)

        public_key = serialize_public_key(self.public_key)
        server_msg = ServerMessage(public_key).serialize()
        person.send_msg(server_msg, encoded=True)

    def _disconnect_client(self, person):
        print('Client {}:{} has disconnected'.format(*person.peer_addr()))
        self.input_sockets.remove(person.sock)
        self.clients.pop(person.peer_addr())
        
        curr_room = self._find_curr_room(person)
        if curr_room:
            curr_room.purge_client(person)

        person.close_sock()

    def start(self):
        while self.input_sockets:
            readable, writable, exceptional = \
                select.select(self.input_sockets, [], self.exceptional_sockets)

            for read_sock in readable:
                if read_sock is self.server_sock:
                    client_sock, client_addr = read_sock.accept()

                    person = Person(client_sock)
                    self.clients[client_addr] = person

                    self._register_client(person)
                else:
                    data = read_sock.recv(settings.BUFFER_SIZE)
                    self._handle_request(read_sock, data)

            for exceptional_sock in exceptional:
                exceptional_sock.close()
                self.clients.pop(exceptional_sock.getpeername())
                self.input_socks.remove(exceptional_sock)

if __name__ == '__main__':
    server = Server(
        settings.SERVER_IP_ADDRESS,
        settings.SERVER_PORT
    )
    server.start()
