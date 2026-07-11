import json
import time

MSG_TYPE_CHAT = "chat"
MSG_TYPE_JOIN = "join"


class Message:
    def __init__(self, room_id, sender_id, nonce, ciphertext, timestamp=None, msg_type=None):
        self.room_id = room_id
        self.sender_id = sender_id
        self.nonce = nonce  # random value to decrypt the message
        self.ciphertext = ciphertext  # the encrypted message 
        self.timestamp = timestamp or time.time()  # defaults to now if not given
        self.msg_type = msg_type or MSG_TYPE_CHAT

    @classmethod
    def encrypt(cls, crypto, room_id, sender_id, plaintext, msg_type=MSG_TYPE_CHAT):
        nonce, ct = crypto.encrypt(plaintext)
        return cls(room_id, sender_id, nonce, ct, msg_type=msg_type)

    def decrypt(self, crypto): # decrypts the message 
        return crypto.decrypt(self.nonce, self.ciphertext)

    def to_wire(self): # converts the message object into bytes
        return json.dumps(self.__dict__).encode("utf-8")

    @staticmethod
    def from_wire(data): # converts the bytes into a message object
        return Message(**json.loads(data.decode("utf-8")))


def build_message(crypto, room_id, sender_id, plaintext, msg_type=MSG_TYPE_CHAT):
    return Message.encrypt(crypto, room_id, sender_id, plaintext, msg_type=msg_type)


def build_join_message(crypto, room_id, sender_id):
    return Message.encrypt(crypto, room_id, sender_id, "joined", msg_type=MSG_TYPE_JOIN)


def read_message(crypto, msg): # wraps decryption of the message
    return msg.decrypt(crypto)
