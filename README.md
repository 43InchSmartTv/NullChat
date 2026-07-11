# NullChat

encrypted peer-to-peer chat.

## running from source

### dependencies

- python 3.11+
- go 1.25+
- tkinter

### setup

```bash
git clone https://github.com/43InchSmartTv/NullChat.git
cd NullChat

pip install -r requirements.txt

cd axl
go build -o node ./cmd/node
cd ..

python -m nullchat
```

on windows the node binary is `node.exe` instead of `node`.

### persistent identity

by default you get a new identity each time you restart. to keep the same one, generate a pem:

```bash
cd axl
openssl genpkey -algorithm ED25519 -out private.pem
```

then add this to `axl/node-config.json`:

```json
"PrivateKeyPath": "private.pem"
```

now your peer id stays the same across restarts.

## how it works

1. create a room and copy the invite token
2. send it to a friend
3. they paste it in "join room"
4. chat with your friend
