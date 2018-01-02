from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend

from elastic import settings
from elastic.message import ServerMessage

def generate_private_key():
    key = rsa.generate_private_key(backend=default_backend(),
                                   public_exponent=65537,
                                   key_size=2048)
    return key

def serialize_public_key(key):
    stream = key.public_bytes(serialization.Encoding.PEM,
                              serialization.PublicFormat.SubjectPublicKeyInfo)
    return stream.decode(settings.ENCODING)

def encrypt_msg(person, msg, encoded=False):
    symmetric_key = Fernet.generate_key()
    f = Fernet(symmetric_key)

    if encoded:
        encoded_msg = msg
    else:
        encoded_msg = msg.encode(settings.ENCODING)

    encrypted_msg = f.encrypt(encoded_msg)
    server_msg = ServerMessage(encrypted_msg)
    
    encrypted_key = person.public_key.encrypt(
        symmetric_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA1()),
            algorithm=hashes.SHA1(),
            label=None
        )
    )
    server_msg.symmetric_key = encrypted_key

    encoded_msg = server_msg.serialize()
    return encoded_msg
