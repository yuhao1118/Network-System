# Request protocal
# {
#     "target": "room:all" | "server" | [username],
#     "task": "chat" | "r" | "u" | "q" | "t",
#     "time": float,
#     "message"?: str
# }

# Response protocal
# {
#     "sender": "room:all" | "server" | [username],
#     "status": "success" | "fail"
#     "task": "chat" | "r" | "u" | "q" | "t",,
#     "time": float,
#     "message": str
# }


import sys
import select
import socket
import time
from urllib import parse


class ChatError(Exception):
    def __init__(self, msg):
        self.msg = msg

    def __repr__(self):
        return str(self.msg).replace("\r", "").replace("\n", "")


SERVER_IP = "127.0.0.1"
SOCK_LIST = []
RECV_BUFFER = 4096
RECV_TIMEOUT = 5
USER_NAMES = {
    # [sock] : [username]
}
PROTO_PREFIX = "chat://chatSever?"

try:
    PORT = int(sys.argv[1])
except:
    print("Incorrect cmd args. Usage: python3 server.py [port]")
    exit()


def encode_url(req_proto):
    # encode dict to chat:// protocol string
    # NUL denotes as End Of String
    return PROTO_PREFIX + parse.urlencode(req_proto) + "NUL"


def decode_url(resp_url):
    # decode a chat:// protocol string to dict
    resp_url = resp_url.replace("NUL", "")
    resp = dict(parse.parse_qsl(parse.urlsplit(resp_url).query))
    for i in ["target", "task", "time"]:
        if i not in resp.keys():
            raise KeyError("Key %s is required in protocol." % i)
    resp["time"] = float(resp["time"])
    return resp


def resp_proto(sender, status, task, message):
    # create a response protocol dict
    proto = {
        "sender": sender,
        "status": status,
        "task": task,
        "message": message,
        "time": time.time()
    }
    return proto


def broadcast_one(sock, sender, status, task, message):
    # broadcast to one client
    for socket in SOCK_LIST:
        if socket == sock:
            resp = encode_url(resp_proto(
                sender, status, task, message)).encode()
            sock.send(resp)


def broadcast_all(sock, sender, status, message):
    # broadcast to one client
    resp = encode_url(resp_proto(
        sender, status, "chat", message)).encode()

    for socket in SOCK_LIST:
        if socket != server_socket and socket != sock:
            socket.send(resp)


def close_sock(sock):
    # safely close a sock and remove it
    sock.close()
    if sock in SOCK_LIST:
        SOCK_LIST.remove(sock)
    if sock in USER_NAMES.keys():
        USER_NAMES.pop(sock)


def list_clients(sock):
    # list out all clients
    sys.stdout.write("Client %s request all current users.\n" %
                     USER_NAMES[sock])
    message = "\rCurrent online users:\n%s\n" % "\n".join(USER_NAMES.values())
    broadcast_one(sock, "server", "success", "u", message)


def target(sock, username):
    # server task :t
    # check if client can chat with an another user
    # broadcast username (if exist) back to the client
    # else broadcast an error msg to the client
    if username not in list(USER_NAMES.values()) + ["room:all"]:
        msg = "\rUser %s is not existed.\n" % username
        sys.stdout.write(
            "Client %s tried to chat with non-exist user %s.\n" % (USER_NAMES[sock], username))
        broadcast_one(sock, "server", "fail", "t", msg)
    else:
        sys.stdout.write("Client %s are now chatting with %s.\n" %
                         (USER_NAMES[sock], username))
        broadcast_one(sock, "server", "success", "t", username)


def username(sock, username):
    # server task :t
    # check if client can rename
    # broadcast new username (if could) back to the client
    # else broadcast an error msg to the client

    # New connetion
    if sock not in USER_NAMES.keys() and username not in USER_NAMES.values():
        msg = "\r%s has joined.\n" % username
        USER_NAMES[sock] = username
        broadcast_all(sock, "server", "success", msg)
        broadcast_one(sock, "server", "success", 'r', USER_NAMES[sock])
    # Username in used
    elif username in USER_NAMES.values():
        if sock not in USER_NAMES.keys():
            msg = "\rUsername %s in used. New connection reject.\n" % username
            broadcast_one(sock, "server", "fail", 'r', msg)
            raise ChatError(msg)
        else:
            msg = "\r%s failed to rename. Username %s in used. Try a new name.\n" % (
                USER_NAMES[sock], username)
            bd_msg = "\rFailed to rename. Username %s in used. Try a new name.\n" % username
            broadcast_one(sock, "server", "fail", 'r', bd_msg)
    # Can update username
    else:
        msg = "\r%s has renamed to %s.\n" % (USER_NAMES[sock], username)
        USER_NAMES[sock] = username
        broadcast_all(sock, "server", "success", msg)
        broadcast_one(sock, "server", "success", 'r', USER_NAMES[sock])

    sys.stdout.write(msg.replace("\r", ""))


def get_sock_by_username(username):
    # get a socket instance by its username (if exist)
    usr_index = list(USER_NAMES.values()).index(username)
    return list(USER_NAMES.keys())[usr_index]


def recvall(sock):
    # Safely receive and concatenate all bytes stream
    # and return decoded dict (if could) request structure
    # else if protocol is illegal, raise an error after TIMEOUT
    # seconds
    start_time = time.time()
    recv = bytes()
    while time.time() - start_time <= RECV_TIMEOUT:
        r, _, _ = select.select([sock], [], [])
        part_recv = sock.recv(RECV_BUFFER)
        if not part_recv:
            raise ChatError("\rClient %s connection lost.\n" %
                            USER_NAMES[sock])
        recv += part_recv
        if recv.decode().startswith(PROTO_PREFIX) and recv.decode().endswith("NUL"):
            return decode_url(recv.decode())
    raise ChatError("\rIllgeal protocol.")


if __name__ == "__main__":
    # Initialise a TCP socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((SERVER_IP, PORT))
    server_socket.listen(10)    # listen up to 10 clients
    SOCK_LIST.append(server_socket)
    sys.stdout.write("Chat server started on port %d\n" % PORT)
    while True:
        try:
            r, _, _ = select.select(SOCK_LIST, [], [])
            for sock in r:
                # Server socket is readable -> accept a new client connection
                if sock == server_socket:
                    sockfd, addr = server_socket.accept()
                    SOCK_LIST.append(sockfd)
                # A client socket is readable -> incomming data
                else:
                    try:
                        recv = recvall(sock)
                        # Message broadcast to whole chat room
                        if recv['target'] == 'room:all':
                            listener = "all"
                            message = "\r<%s> %s" % (
                                USER_NAMES[sock], recv['message'])
                            broadcast_all(sock, "room:all", "success", message)
                            sys.stdout.write(
                                "Client %s broadcasted a message to all.\n" % USER_NAMES[sock])
                        # Message broadcast to a user
                        elif recv['target'] in USER_NAMES.values():
                            message = "\r<%s> %s" % (
                                USER_NAMES[sock], recv['message'])
                            target_sock = get_sock_by_username(recv['target'])
                            broadcast_one(
                                target_sock, recv['target'], "success", "chat", message)
                            sys.stdout.write(
                                "Client %s broadcasted a message to %s.\n" % (USER_NAMES[sock], USER_NAMES[target_sock]))
                        # Request a server task
                        elif recv['target'] == 'server':
                            # Rename client
                            if recv['task'] == "r":
                                username(sock, recv['message'])
                            # List all current users
                            elif recv['task'] == 'u':
                                list_clients(sock)
                            # Close client connection
                            elif recv['task'] == 'q':
                                raise ChatError(
                                    "Client %s quit normally." % USER_NAMES[sock])
                            # Choose a target user to send message
                            elif recv['task'] == 't':
                                target(sock, recv['message'])

                    except Exception as e:
                        # Any error here will cause a client go down
                        # The server remains functionailty
                        msg = repr(e) + "\n"
                        sys.stdout.write(msg)
                        sys.stdout.flush()
                        if sock in USER_NAMES.keys():
                            message = "\r%s has left.\n" % USER_NAMES[sock]
                            sys.stdout.write(message.replace("\r", ""))
                            broadcast_all(sock, "server", "success", message)
                        close_sock(sock)
        except:
            # Any error here will cause the server go down
            # Close as many socket connection as possible
            sys.stdout.write("Close all sockets. Close the server.\n")
            for sock in SOCK_LIST:
                close_sock(sock)
            exit()
