import pickle

class Message:

    def serialize(self):
        return pickle.dumps(self)

class ClientMessage(Message):

    def __init__(self, text, public_key=None):
        self.text = text
        self.public_key = public_key

class ServerMessage(Message):

    def __init__(self, text):
        self.text = text
        self.symmetric_key = None
