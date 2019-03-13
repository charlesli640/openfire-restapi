import ssl
from socket import socket, AF_INET, SOCK_DGRAM
from dtls import do_patch
do_patch()
sock = ssl.wrap_socket(socket(AF_INET, SOCK_DGRAM))
sock.connect(('35.197.98.183', 10000))
sock.send('Hi there')
