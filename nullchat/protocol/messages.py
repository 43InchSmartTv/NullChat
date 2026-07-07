import json
import time

class Message:
    def __init__(self, room_id, sender_id, nonce, ciphertext, timestamp=None):
        self.room_id = room_id
        self.sender_id = sender_id
        self.nonce = nonce  # random value to decrypt the message
        self.ciphertext = ciphertext  # the encrypted message 
        self.timestamp = timestamp or time.time()  # defaults to now if not given

    @classmethod
    def encrypt(cls, crypto, room_id, sender_id, plaintext): # creates a message object
        nonce, ct = crypto.encrypt(plaintext)
        return cls(room_id, sender_id, nonce, ct)

    def decrypt(self, crypto): # decrypts the message 
        return crypto.decrypt(self.nonce, self.ciphertext)

    def to_wire(self): # converts the message object into bytes
        return json.dumps(self.__dict__).encode("utf-8")

    @staticmethod
    def from_wire(data): # converts the bytes into a message object
        return Message(**json.loads(data.decode("utf-8")))


def build_message(crypto, room_id, sender_id, plaintext):
    return Message.encrypt(crypto, room_id, sender_id, plaintext)


def read_message(crypto, msg):
    return msg.decrypt(crypto)