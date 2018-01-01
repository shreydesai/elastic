import socket
import select

from elastic import settings
from elastic.person import Person
from elastic.room import Room

class Server:

    def __init__(self):
        self.input_sockets = []
        self.exceptional_sockets = []
        self.server_sock = self._connect()

        self.clients = {}
        self.rooms = {}

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

    def _find_curr_room(self, person):
        for room in self.rooms.values():
            if room.search_client(person):
                return room
        return None

    def _handle_request(self, read_sock, data):
        person = self.clients[read_sock.getpeername()]

        if data:
            success = True
            msg = data.decode(settings.ENCODING).strip()

            print('Received {} from {}:{}'.format(data, *person.peer_addr()))

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
              '/join <name> - Joins a room named <name>. If <name> does ' + \
              'not exist, then it will be created.\n' + \
              '/list - Lists all rooms.\n'
        person.send_msg(msg)

    def _join(self, person, msg):
        parts = msg.split(' ')

        if len(parts) < 2:
            return False

        _, name = parts
        name = name.strip()

        room = None
        curr_room = self._find_curr_room(person)

        if name in self.rooms:
            room = self.rooms[name]

            if room.search_client(person):
                msg = 'You are already in room \'{}\''.format(name)
                person.send_msg(msg)
                return True
        else:
            room = Room(name, person)
            self.rooms[name] = room

        if curr_room:
            curr_room.remove_client(person)

        room.add_client(person)

        return True

    def _list(self, person):
        string = ['Room\tClients']
        for name in sorted(self.rooms):
            room = self.rooms[name]
            string.append('{}\t{}'.format(room.name, len(room.clients)))
        msg = '\n'.join(string) + '\n'
        person.send_msg(msg)

    def _register_client(self, person):
        print('Client {}:{} connected'.format(*person.peer_addr()))
        self.input_sockets.append(person.sock)
        self._help(person)

    def _disconnect_client(self, person):
        print('Client {}:{} has disconnected'.format(*person.peer_addr()))
        self.input_sockets.remove(person.sock)
        self.clients.pop(person.peer_addr())
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
    server = Server()
    server.start()
