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


import socket
import select
import sys
import time
import re
from urllib import parse


RECV_BUFFER = 4
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
    proto = {
        "target": target,
        "task": task,
        "message": message,
        "time": time.time()
    }
    return proto


def encode_url(req_proto):
    return PROTO_PREFIX + parse.urlencode(req_proto) + "NUL"


def decode_url(resp_url):
    resp_url = resp_url.replace("NUL", "")
    resp = dict(parse.parse_qsl(parse.urlsplit(resp_url).query))
    resp["time"] = float(resp["time"])
    return resp


def recvall(sock):
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
    mat_res = re.match(r'^:([u|r|q|t])\s?(.*)$', raw_message)
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


def close_sock(sock, msg, code=0):
    sock.close()
    SOCK_LIST.remove(sock)
    sys.stdout.write("\r%s\n" % msg)
    exit(code)


def main():
    usr_name = input("Input username: ")
    msg = ""
    target = "room:all"
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)
    SOCK_LIST.append(s)

    try:
        s.connect((SERVER_IP, PORT))
        send(s, 'server', ":r %s" % usr_name)
        select.select([s, sys.stdin], [], [])
        send(s, 'server', ":t %s" % target)
    except:
        close_sock(s, "Unable to connect. Che")
    prompt()
    while True:
        try:
            r, _, _ = select.select(
                SOCK_LIST, [], [])

            for sock in r:
                if sock == s:
                    recv = recvall(sock)
                    msg = recv['data']
                    if recv['status'] == "success":
                        if recv['task'] == 't':
                            msg = "\rYou are now chatting with %s.\n" % recv['data']
                            target = recv['data']
                        elif recv['task'] == 'r':
                            msg = "\rYour username is %s.\n" % recv['data']
                            usr_name = recv['data']
                    sys.stdout.write(msg)
                    prompt()
                else:
                    msg = sys.stdin.readline()
                    send(s, target, msg)
                    prompt()
        except:
            close_sock(s, "Connection is closed by chat server.")


if __name__ == "__main__":
    main()
