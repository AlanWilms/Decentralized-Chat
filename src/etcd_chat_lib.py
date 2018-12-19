import subprocess
import os
import time
import errno
import rsa
from cryptography.fernet import Fernet


class EtcdChatLib:
    def __init__(self, private_ip):
        self.etcd_dir = os.path.expanduser('~/etcd/bin/')
        self.chat_dir = os.path.expanduser('~/group-project-NOP/')
        self.endpoints = [private_ip + ":2380"]
        self.private_keys = {}
        self.public_keys = {}

    def add_endpoint(self, ip_addr):
	self.endpoints.append(ip_addr + ":2380")

    def get(self, key):
        val = subprocess.check_output([self.etcd_dir + "etcdctl", "--endpoints=" + ",".join(self.endpoints), "get", key])
        if len(val.split("\n")) < 2:
            return None
        return val.split("\n")[1]

    def put(self, key, val):
        status = subprocess.check_output([self.etcd_dir + "etcdctl", "--endpoints=" + ",".join(self.endpoints), "put", key, val])
        if status.strip() != "OK":
            raise LookupError("Database seems to be down!")

    def get_chatrooms(self):
        '''Get list of chatrooms from etcd instance'''
        val = self.get("meta/chatrooms")
        if not val:
            return []
        return val.split("/")

    def get_members(self, chatroom):
        '''Get list of members for a chat from etcd instance'''
        val = self.get("/".join(["meta", chatroom, "members"]))
        if not val:
            return []
        return val.split("/")

    def get_num_members(self, chatroom):
        return int(self.get("/".join(["meta", chatroom, "num_members"])))

    def add_chatroom(self, user, name):
        rooms = self.get_chatrooms()
        if name in rooms:
            raise KeyError("Duplicate room name!")
        rooms.append(name)

        # Add chatroom to metadata
        self.put("meta/chatrooms", "/".join(rooms))

        # Set num_messages for chatroom to 0
        self.put("/".join(["meta", name, "num_messages"]), "0")

        # Add initial user of chat to members
        self.put("/".join(["meta", name, "members"]), user)

        # Set num_members for chatroom to 1
        self.put("/".join(["meta", name, "num_members"]), "1")

        # Generate RSA keys
        public_key, private_key = rsa.newkeys(512)

        # Store public key in etcd
        self.put("/".join(["meta", name, "public_key"]), "/".join([str(public_key.n), str(public_key.e)]))

        # Store private key in local folder 
        private_key_filename = self.chat_dir + "private_keys/" + name + ".pem"
        self._save_private_key(private_key, private_key_filename)

    def remove_chatroom(self, name):
        rooms = self.get_chatrooms()
        if name not in rooms:
            raise KeyError("Room name does not exist!")
        rooms.remove(name)
        self.put("meta/chatrooms", "/".join(rooms))

    def join_chatroom(self, user, chatroom):
        members = self.get_members(chatroom)
        if user in members:
            raise KeyError("User with same name already in chatroom!")

        # Generate RSA keys
        public_key, private_key = rsa.newkeys(512)

        # Store public key in etcd
        self.put("/".join(["meta", chatroom, user, "public_key"]), "/".join([str(public_key.n), str(public_key.e)]))

        # Add default value to encrypted private key receiver
        self.put("/".join(["meta", chatroom, user, "encrypted_private_key"]), "NULL".encode("hex"))

        # Get members again to prevent race condition
        members = self.get_members(chatroom)

        # Add user to member metadata
        members.append(user)
        self.put("/".join(["meta", chatroom, "members"]), "/".join(members))

        # Update num_members (which triggers other members receiving the new member, so must be done last)
        self.put("/".join(["meta", chatroom, "num_members"]), str(len(members)))

        # Wait until encrypted_private_key is updated
        encrypted_private_key = "NULL"
        while encrypted_private_key == "NULL":
            encrypted_private_key = self.get("/".join(["meta", chatroom, user, "encrypted_private_key"])).decode("hex")
            time.sleep(1)

        # Decrypt and save chatroom private key
        encrypted_aes_key = self.get("/".join(["meta", chatroom, user, "encrypted_aes_key"])).decode("hex")
        chatroom_private_key = rsa.PrivateKey.load_pkcs1(self._aes_decrypt(encrypted_private_key, encrypted_aes_key, private_key))

        private_key_filename = self.chat_dir + "private_keys/" + chatroom + ".pem"
        self._save_private_key(chatroom_private_key, private_key_filename)

    def approve_member(self, user, chatroom):
        '''Approves a user join request by encrypting the chatroom private key with the prospective member's public key and sending it'''
        chatroom_private_key_pem = self._load_private_key(chatroom).save_pkcs1()

        val = self.get("/".join(["meta", chatroom, user, "public_key"]))
        if not val:
            return
        user_public_key = rsa.PublicKey(*map(int, val.split("/")))
        
        # Encrypt chatroom private key
        encrypted_aes_key, encrypted_msg = self._aes_encrypt(chatroom_private_key_pem, user_public_key)

        # Store encrypted aes key and private rsa key in etcd
        self.put("/".join(["meta", chatroom, user, "encrypted_aes_key"]), encrypted_aes_key.encode("hex"))
        self.put("/".join(["meta", chatroom, user, "encrypted_private_key"]), encrypted_msg.encode("hex"))

    def get_num_messages(self, chatroom):
        return int(self.get("meta/" + chatroom + "/num_messages"))

    def send(self, chatroom, user, msg):
        # Get public key
        rsa_public_key = self._load_public_key(chatroom)

        # Encrypt message
        encrypted_aes_key, encrypted_msg = self._aes_encrypt(msg, rsa_public_key)

        num_messages = self.get_num_messages(chatroom)
        # Add message
        self.put("/".join(["chats", chatroom, str(num_messages)]), encrypted_msg.encode("hex"))
        # Add encrypted aes key
        self.put("/".join(["chats", chatroom, str(num_messages), "encrypted_aes_key"]), encrypted_aes_key.encode("hex"))
        # Add user
        self.put("/".join(["chats", chatroom, str(num_messages), "author"]), user)
        # Update num_messages
        self.put("meta/" + chatroom + "/num_messages", str(num_messages + 1))

    def recv(self, chatroom, msg_id):
        encrypted_msg = self.get("/".join(["chats", chatroom, str(msg_id)])).decode("hex")
        encrypted_aes_key = self.get("/".join(["chats", chatroom, str(msg_id), "encrypted_aes_key"])).decode("hex")

        user = self.get("/".join(["chats", chatroom, str(msg_id), "author"]))
        
        rsa_private_key = self._load_private_key(chatroom)
        msg = self._aes_decrypt(encrypted_msg, encrypted_aes_key, rsa_private_key)
        return user, msg

    def _aes_encrypt(self, msg, rsa_public_key):
        aes_key = Fernet.generate_key()
        aes_cipher = Fernet(aes_key)
        ciphertext = aes_cipher.encrypt(msg)

        encrypted_aes_key = rsa.encrypt(aes_key.encode("utf8"), rsa_public_key)
        return encrypted_aes_key, ciphertext

    def _aes_decrypt(self, msg, encrypted_aes_key, rsa_private_key):
        aes_key = rsa.decrypt(encrypted_aes_key, rsa_private_key)
        aes_cipher = Fernet(aes_key)
        
        return aes_cipher.decrypt(msg)

    def _save_private_key(self, private_key, private_key_filename):
	if not os.path.exists(os.path.dirname(private_key_filename)):
            try:
                os.makedirs(os.path.dirname(private_key_filename))
            except OSError as exc: # Guard against race condition
                if exc.errno != errno.EEXIST:
                    raise
        with open(private_key_filename, "w") as f:
            f.write(private_key.save_pkcs1())

    def _load_private_key(self, chatroom):
        if chatroom in self.private_keys:
            return self.private_keys[chatroom]
        private_key_filename = self.chat_dir + "private_keys/" + chatroom + ".pem" 
	if not os.path.isfile(private_key_filename):
            raise RuntimeError("Private key file not found: " + private_key_filename)
        with open(private_key_filename, "rb") as f:
            keydata = f.read()
        self.private_keys[chatroom] = rsa.PrivateKey.load_pkcs1(keydata) 
        return self.private_keys[chatroom]

    def _load_public_key(self, chatroom):
        if chatroom in self.public_keys:
            return self.public_keys[chatroom]
        self.public_keys[chatroom] = rsa.PublicKey(*map(int, self.get("/".join(["meta", chatroom, "public_key"])).split("/")))
        return self.public_keys[chatroom]
