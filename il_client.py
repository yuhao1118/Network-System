import socket
import select
import sys


def start_client():
    serverName = "127.0.0.1"
    serverPort = 8888
    clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    clientSocket.settimeout(2)
    clientSocket.connect((serverName, serverPort))
    msg = "chat://chatSever?target=server&task=r&time=1613014107.254594NUL"
    clientSocket.send(msg.encode())
    recv = clientSocket.recv(4096)
    print(recv.decode())
    # clientSocket.close()


if __name__ == "__main__":
    start_client()
