from elastic import settings

class Person:

    def __init__(self, sock, name=None):
        self.sock = sock
        self.name = name
        self.public_key = None

        self.sock.setblocking(0)

    def __eq__(self, obj):
        if isinstance(obj, Person):
            return self.__dict__ == obj.__dict__
        return NotImplemented

    def __repr__(self):
        return 'Person<{}>'.format(self.name)

    def addr(self):
        return self.sock.getsockname()

    def peer_addr(self):
        return self.sock.getpeername()

    def close_sock(self):
        self.sock.close()

    def send_msg(self, msg, encoded=False):
        if encoded:
            self.sock.send(msg)
        else:
            encoded_msg = msg.encode(settings.ENCODING)
            self.sock.send(encoded_msg)
