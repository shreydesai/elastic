from elastic import settings

class Room:

    def __init__(self, name, admin):
        self.name = name
        self.admin = None
        self.clients = []

    def __eq__(self, obj):
        if isinstance(obj, Room):
            return self.name == obj.name
        return NotImplemented

    def __repr__(self):
        return 'Room<{}>'.format(self.name)

    def add_client(self, person):
        self.clients.append(person)
        msg = '[{}:{}] has joined room \'{}\''.format(
            *person.peer_addr(), self.name
        )
        for client in self.clients:
            if client is person:
                msg = 'Joined room \'{}\' ({} client(s) present)\n'
                msg = msg.format(self.name, len(self.clients) - 1)
            client.send_msg(msg)

    def remove_client(self, person):
        self.clients.remove(person)
        person.send_msg('Left room \'{}\'\n'.format(self.name))
        msg = '[{}:{}] has left room \'{}\''.format(
            *person.peer_addr(), self.name
        )
        for client in self.clients:
            client.send_msg(msg)

    def search_client(self, client):
        return client in self.clients

    def broadcast(self, sender, msg):
        broadcast_msg = None
        for client in self.clients:
            if client is sender:
                broadcast_msg = settings.ACK
            else:
                broadcast_msg = '[{}:{}] {}'.format(*client.peer_addr(), msg)
            client.send_msg(broadcast_msg)
