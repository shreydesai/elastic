from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend

from elastic import settings
from elastic.utils import encrypt_msg

class Room:

    def __init__(self, name, admin):
        self.name = name
        self.admin = None
        self.key = None
        self.clients = []

    def __eq__(self, obj):
        if isinstance(obj, Room):
            return self.name == obj.name
        return NotImplemented

    def __repr__(self):
        return 'Room<{}>'.format(self.name)

    def is_protected(self):
        return self.key is not None

    def set_key(self, key):
        self.key = hash(key)

    def correct_key(self, key):
        return self.key == hash(key) 

    def add_client(self, person):
        self.clients.append(person)
        msg = '[{}:{}] has joined room \'{}\''.format(
            *person.peer_addr(), self.name
        )
        for client in self.clients:
            if client is person:
                msg = 'Joined{}room \'{}\' ({} client(s) present)\n'
                msg = msg.format(' protected ' if self.is_protected() else ' ',
                                 self.name, len(self.clients) - 1)
            encoded_msg = encrypt_msg(client, msg)
            client.send_msg(encoded_msg, encoded=True)

    def remove_client(self, person):
        self.purge_client(person)

        msg = 'Left room \'{}\'\n'.format(self.name)
        encoded_msg = encrypt_msg(person, msg)
        person.send_msg(encoded_msg, encoded=True)

        msg = '[{}:{}] has left room \'{}\''.format(
            *person.peer_addr(), self.name
        )

        for client in self.clients:
            encoded_msg = encrypt_msg(client, msg)
            client.send_msg(encoded_msg, encoded=True)

    def purge_client(self, person):
        self.clients.remove(person)

    def search_client(self, client):
        return client in self.clients

    def broadcast(self, sender, msg):
        for client in self.clients:
            if client is sender:
                broadcast_msg = settings.ACK
            else:
                broadcast_msg = '[{}:{}] {}'.format(*client.peer_addr(), msg)

            encoded_msg = encrypt_msg(client, broadcast_msg)
            client.send_msg(encoded_msg, encoded=True)
