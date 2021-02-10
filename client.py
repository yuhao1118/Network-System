# Request protocal
# {
#     "target": "room:all" | "server" | [username],
#     "task": "chat" | "r" | "u" | "q" | "t",
#     "time": float,
#     "message": str
# }

# Response protocal
# {
#     "sender": "room:all" | "server" | [username],
#     "status": "success" | "fail"
#     "task": "chat" | "r" | "u" | "q" | "t",,
#     "time": float,
#     "data": str
# }


import socket
import select
import sys
import time
import re
from urllib import parse


RECV_BUFFER = 4096
PROTO_PREFIX = "chat://chatSever?"
SOCK_LIST = [sys.stdin]

try:
    if (len(sys.argv) < 3):
        raise Exception
    SERVER_IP = sys.argv[1]
    PORT = int(sys.argv[2])
except:
    print("Incorrect cmd args. Try: python client.py [host] [port]")
    exit(1)


def prompt():
    sys.stdout.write('<You> ')
    sys.stdout.flush()


def req_proto(target, task, message):
    # create a response protocol dict
    proto = {
        "target": target,
        "task": task,
        "message": message,
        "time": time.time()
    }
    return proto


def encode_url(req_proto):
    # encode dict to chat:// protocol string
    # NUL denotes as End Of String
    return PROTO_PREFIX + parse.urlencode(req_proto) + "NUL"


def decode_url(resp_url):
    # decode a chat:// protocol string to dict
    resp_url = resp_url.replace("NUL", "")
    resp = dict(parse.parse_qsl(parse.urlsplit(resp_url).query))
    resp["time"] = float(resp["time"])
    return resp


def recvall(sock):
    # Safely receive and concatenate all bytes stream
    # and return decoded dict request structure
    recv = bytes()
    while True:
        r, _, _ = select.select([sock], [], [])
        part_recv = sock.recv(RECV_BUFFER)
        if not part_recv:
            raise Exception
        recv += part_recv
        if recv.decode().startswith(PROTO_PREFIX) and recv.decode().endswith("NUL"):
            return decode_url(recv.decode())


def send(sock, target, raw_message):
    # parse and send a message

    mat_res = re.match(r'^:([u|r|q|t])\s?(.*)$', raw_message)
    # :u                    ** Fetch all clients name> **
    # :q                    ** Close connection and quit **
    # :r <new_name>         ** Rename current client **
    # :t <target_username>  ** Send msg to target user **
    if mat_res:
        opt, val = mat_res.group(1), mat_res.group(2)
        req = encode_url(req_proto("server", opt, val)).encode()
        if ((opt == "r" or opt == "t") and val != "") or ((opt == "u" or opt == "q") and val == ""):
            sock.send(req)
        else:
            sys.stdout.write("\rCommand incorrect.\n")

    else:
        req = encode_url(req_proto(target, "chat", raw_message)).encode()
        sock.send(req)


def close_sock(sock, msg):
    # safely close a sock and remove it
    sock.close()
    if sock in SOCK_LIST:
        SOCK_LIST.remove(sock)
    sys.stdout.write("\r%s\n" % msg)
    exit()


if __name__ == "__main__":
    usr_name = input("Input username: ")
    target = "room:all"  # enter global chat room by default

    # Initialise a client socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)
    SOCK_LIST.append(s)

    try:
        # Connect to server and send username and default target
        s.connect((SERVER_IP, PORT))
        send(s, 'server', ":r %s" % usr_name)
        select.select([s, sys.stdin], [], [])
        send(s, 'server', ":t %s" % target)
    except:
        close_sock(s, "Unable to connect.")

    prompt()
    while True:
        try:
            r, _, _ = select.select(SOCK_LIST, [], [])
            for sock in r:
                # if client socket is readable -> incomming data
                if sock == s:
                    recv = recvall(sock)
                    msg = recv['message']
                    if recv['status'] == "success":
                        # Server tasks success. Update local variable
                        if recv['task'] == 't':
                            msg = "\rYou are now chatting with %s.\n" % recv['message']
                            target = recv['message']
                        elif recv['task'] == 'r':
                            msg = "\rYour username is %s.\n" % recv['message']
                            usr_name = recv['message']
                    # Display any msg from server
                    sys.stdout.write(msg)
                    prompt()
                else:
                    # stdin is readable -> send
                    msg = sys.stdin.readline()
                    send(s, target, msg)
                    prompt()
        except:
            close_sock(s, "Connection is closed by chat server.")
