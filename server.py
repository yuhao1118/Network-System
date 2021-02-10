# Request protocal
# {
#     "target": "room:all" | "server" | [username],
#     "task": "chat" | "r" | "u" | "q" | "t",
#     "time": float,
#     "message": str
# }

# Response protocal
# {
#     "sender": "chat" | "server""
#     "status": "success" | "fail"
#     "task": str,
#     "time": float,
#     "data": str
# }


import sys
import select
import socket
import time
from urllib import parse


class ChatError(Exception):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return str(self.msg)


SERVER_IP = "127.0.0.1"
SOCK_LIST = []
RECV_BUFFER = 4
USER_NAMES = {}
PROTO_PREFIX = "chat://chatSever?"
server_socket = None

try:
    PORT = int(sys.argv[1])
except:
    print("Incorrect cmd args. Try: python server.py [port]")
    exit(1)


def encode_url(req_proto):
    return PROTO_PREFIX + parse.urlencode(req_proto) + "NUL"


def decode_url(resp_url):
    resp_url = resp_url.replace("NUL", "")
    resp = dict(parse.parse_qsl(parse.urlsplit(resp_url).query))
    resp["time"] = float(resp["time"])
    return resp


def resp_proto(sender, status, task, data=None):
    proto = {
        "sender": sender,
        "status": status,
        "task": task,
        "data": data,
        "time": time.time()
    }
    return proto


def broadcast_one(sock, sender, status, task, message):
    for socket in SOCK_LIST:
        if socket == sock:
            resp = encode_url(resp_proto(
                sender, status, task, message)).encode()
            sock.send(resp)


def broadcast_all(sock, sender, status, message):
    resp = encode_url(resp_proto(
        sender, status, "chat", message)).encode()

    for socket in SOCK_LIST:
        if socket != server_socket and socket != sock:
            socket.send(resp)


def close_sock(sock):
    sock.close()
    SOCK_LIST.remove(sock)
    if sock in USER_NAMES.keys():
        USER_NAMES.pop(sock)


def list_clients(sock):
    sys.stdout.write("Client %s request all current users.\n" %
                     USER_NAMES[sock])
    message = "\rCurrent online users:\n%s\n" % "\n".join(USER_NAMES.values())
    broadcast_one(sock, "server", "success", "u", message)


def target(sock, username):
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
    msg = ""
    if sock not in USER_NAMES.keys() and username not in USER_NAMES.values():
        msg = "\r%s has joined.\n" % username
        USER_NAMES[sock] = username
        broadcast_all(sock, "server", "success", msg)
        broadcast_one(sock, "server", "success", 'r', USER_NAMES[sock])

    elif username in USER_NAMES.values():
        if sock not in USER_NAMES.keys():
            msg = "\rUsername %s in used. New connection reject.\n" % username
            broadcast_one(sock, "server", "fail", 'r', msg)
            raise ChatError(msg)
        else:
            msg = "\rUsername %s in used. Try a new name.\n" % username
            broadcast_one(sock, "server", "fail", 'r', msg)
    else:
        msg = "\r%s has renamed to %s.\n" % (USER_NAMES[sock], username)
        USER_NAMES[sock] = username
        broadcast_all(sock, "server", "success", msg)
        broadcast_one(sock, "server", "success", 'r', USER_NAMES[sock])

    sys.stdout.write(msg.replace("\r", ""))


def get_sock_by_username(username):
    usr_index = list(USER_NAMES.values()).index(username)
    return list(USER_NAMES.keys())[usr_index]


def recvall(sock):
    recv = bytes()
    while True:
        r, _, _ = select.select([sock], [], [])
        part_recv = sock.recv(RECV_BUFFER)
        if not part_recv:
            raise ChatError("\rClient %s connection lost.\n" %
                            USER_NAMES[sock])
        recv += part_recv
        if recv.decode().startswith(PROTO_PREFIX) and recv.decode().endswith("NUL"):
            return recv


def main():
    global server_socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((SERVER_IP, PORT))
    server_socket.listen(10)

    SOCK_LIST.append(server_socket)

    sys.stdout.write("Chat server started on port %d\n" % PORT)
    while True:
        try:
            r, _, _ = select.select(
                SOCK_LIST, [], [])

            for sock in r:
                if sock == server_socket:
                    sockfd, addr = server_socket.accept()
                    SOCK_LIST.append(sockfd)
                else:
                    try:
                        recv = decode_url(recvall(sock).decode())
                        if recv['target'] == 'room:all':
                            listener = "all"
                            message = "\r<%s> %s" % (
                                USER_NAMES[sock], recv['message'])
                            broadcast_all(sock, "room:all", "success", message)
                            sys.stdout.write(
                                "Client %s broadcasted a message to all.\n" % USER_NAMES[sock])
                        elif recv['target'] in USER_NAMES.values():
                            message = "\r<%s> %s" % (
                                USER_NAMES[sock], recv['message'])
                            target_sock = get_sock_by_username(recv['target'])
                            broadcast_one(
                                target_sock, recv['target'], "success", "chat", message)
                            sys.stdout.write(
                                "Client %s broadcasted a message to %s.\n" % (USER_NAMES[sock], USER_NAMES[target_sock]))
                        elif recv['target'] == 'server':
                            if recv['task'] == "r":
                                username(sock, recv['message'])
                            elif recv['task'] == 'u':
                                list_clients(sock)
                            elif recv['task'] == 'q':
                                raise ChatError("")
                            elif recv['task'] == 't':
                                target(sock, recv['message'])

                    except Exception as e:
                        if isinstance(e, ChatError):
                            msg = str(e).replace("\r", "")
                            sys.stdout.write(msg)
                        if sock in USER_NAMES.keys():
                            message = "\r%s has left.\n" % USER_NAMES[sock]
                            sys.stdout.write(message.replace("\r", ""))
                            broadcast_all(sock, "server", "success", message)
                        close_sock(sock)
        except:
            sys.stdout.write("Close all sockets. Close the server\n")
            for sock in SOCK_LIST:
                sock.close()
            exit()


if __name__ == "__main__":
    main()
