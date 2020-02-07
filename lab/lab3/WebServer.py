"""
Python version: 3.7.4 use Python3!
Author: z5219960@unsw.edu.au Heng-Chuan Lin
description: COMP3331 lab3_EX4 building a simple Web server dealing with Get HTTP method.
"""

import sys
from socket import *

# check the command line format is correct
if len(sys.argv) == 1 or len(sys.argv) > 2:
    sys.exit('Usage: python3 WebServer <PortNumber>')

# check the Port number is in correct range.
try:
    Port = int(sys.argv[1])  # take the port number from command line argv
    if Port < 1024 or Port == 8080:
        raise ValueError
except ValueError:
    sys.exit('Error: Port number should be digit only and >1024 but != 8080')

# create server's socket (IPv4,TCP)
serverSocket = socket(AF_INET, SOCK_STREAM)

# server runs on localhost(i.e. 127.0.0.1)
serverSocket.bind(('localhost', Port))

# server enable listen mode
serverSocket.listen(1)

print("The server is ready to receive on Port: %d" % (Port))

# keep listening on this port
while True:
    # invoke accept() when client send request
    connectionSocket, addr = serverSocket.accept()

    # try-and-except use for checking whether the requested obj is in the directory or not.
    try:
        request = connectionSocket.recv(1024)                                           # take the request message from client
        requested_obj = request.decode().split(' ')[1]                                  # decode byte obj then parse the string to obtain requested obj
        requested_obj = requested_obj.replace('/', '')                                  # remove '/'
        if requested_obj == '':                                                         # redirect to index.html if requested_obj == ''
            requested_obj = 'index.html'
        if '.html' in requested_obj:                                                    # html part
            obj_file = open(requested_obj)                                              # open and read file
            obj_content = obj_file.read()
            connectionSocket.send('HTTP/1.1 200 OK\r\n'.encode())                       # send the 200 status code
            connectionSocket.send('Content-Type: text/html\r\n'.encode())               # send the content-type, telling the broswer it's html
            connectionSocket.send("\r\n".encode())                                      # send the nextline to jump to content part
            connectionSocket.send(obj_content.encode())                                 # send the encoded content
            obj_file.close()                                                            # close the file
        elif '.jpg' in requested_obj:
            obj_file = open(requested_obj, 'rb')                                        # open and read file in binary way
            obj_content = obj_file.read()
            connectionSocket.send('HTTP/1.1 200 OK\r\n'.encode())                      # send the 200 status code
            connectionSocket.send('Content-Type: image/jpeg\r\n'.encode())             # send the content-type, telling the broswer it's jpg
            connectionSocket.send("Accept-Ranges: bytes\r\n".encode())                 # send the info to tell the broswer that the unit for ranges are bytes.
            connectionSocket.send("\r\n".encode())                                     # send the nextline to jump to content part
            connectionSocket.send(obj_content)                                          # send the content
            obj_file.close()                                                             # close the file
        connectionSocket.close()                                                        #close this connection socket
    except:
        connectionSocket.send('HTTP/1.1 404 Not Found\r\n'.encode())                     # send the 404 status code
        connectionSocket.send('Content-Type: text/html\r\n'.encode())                   # send the content-type, telling the broswer it's html
        connectionSocket.send("\r\n".encode())                                           # send the nextline to jump to content part
        connectionSocket.send(                                                           # send the encoded content
            '<html><head><title>404</title></head><body><p>404 Page not found '
            '(this customized page is made by z5219960)'
            '</p></body></html>'.encode())
        connectionSocket.close()                                                        #close this connection socket
