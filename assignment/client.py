"""
Python version: python3.7 use python3 command
Author : Lin, Heng-Chuan (z5219960@unsw.edu.au)

description: Client for COMP9331 Assignment
            Support TCP connection and Peer-to-Peer message
"""
import threading
from socket import *
import sys

'''
Threading function  
'''


def ConnectionHolder():

    """
    threading function for connectionHolder
    basically hanlding every response from Server
    """

    global clientSocket
    global P2P_thread
    global P2P_contact
    logout = False
    while True:
        if logout:
            # if you've logout, shut this thread function down ( this would cause termination of entire program)
            break
        try:
            # keep waiting for msg
            response = clientSocket.recv(1024)
            if not response:
                break
            response_list = response.decode().split('\r\n')
            for msg in response_list:
                if msg == 'LOGOUT':
                    # get the msg from Server saying that you've been logout
                    print("[Server] You've been logged out from Server")
                    print()
                    print("[P2P][Notification] You can still chat with your Peers if you have any")
                    print()
                    print("[Local] command exit() to exit if you wish")
                    print()
                    logout = True                                             #terminate the thread then entire program
                elif msg[:16] == 'Ini_P2P_connect ':
                    # this is the response that You send StartPrivate command to server
                    [command, client_to_connect, ipaddr, port] = msg.split()
                    # handle the reconnection P2P or first connection P2P
                    if client_to_connect not in P2P_contact.keys():   # either not P2P_thread[client_to_connect].is_alive() is ok
                        print('StartPrivate initialized successfully')
                        print()                                               # make terminal looking wholesome
                        # Now initialize the thread for connect to client
                        # to connect, need to know the Peer's IP and Port
                        P2P_thread[client_to_connect] = threading.Thread(name="P2Pconn", target=P2PConnector,
                                                                         args=(client_to_connect, ipaddr, int(port)))
                        P2P_thread[client_to_connect].daemon = True
                        P2P_thread[client_to_connect].start()
                    elif client_to_connect in P2P_contact.keys():
                        print('[P2P][Error] You have already set up the P2P connection with ' + client_to_connect)
                        print()
                    else:
                        print('[P2P][Error] failed initiation of P2P Connector')
                        print()
                elif msg[:15] == 'Ini_P2P_listen ':
                    # someone send StartPrivate command to server and tell you get prepared for listening
                    [command, client_to_listen] = msg.split()
                    if client_to_listen not in P2P_contact.keys():
                        P2P_thread[client_to_listen] = threading.Thread(name="P2Pconn", target=P2PReceiver,
                                                                        args=(client_to_listen,))
                        P2P_thread[client_to_listen].daemon = True
                        P2P_thread[client_to_listen].start()
                    elif client_to_listen in P2P_contact.keys():
                        print('[P2P][Error] You have already set up the P2P connection with ' + client_to_listen)
                        print()
                    else:
                        print('[P2P][Error] failed initiation of P2P Receiver')
                        print()
                elif msg != '':
                    print(msg)
                    print()
        except:
            continue
    clientSocket.close()
    return


def P2PConnector(client, ip, port):
    """
    Set up a thread for connecting to the Peer
    for a single Peering, either Connector or Receiver thread being created.
    :param client: Peer whom you connect to
    :param ip: Peer's IP address
    :param port: Peer's Port
    """
    global P2P_contact
    print('[P2P][Connector-thread] Start P2P with ' + client)
    print()
    # Now connect to Peer
    mySocket_P2P = socket(AF_INET, SOCK_STREAM)
    mySocket_P2P.connect((ip, port))
    # Record the connSocket
    P2P_contact[client] = mySocket_P2P
    while True:
        if client not in P2P_contact.keys():
            # tracking whether the Peer is removed or not ( this would terminate this Thread )
            break
        try:
            response = mySocket_P2P.recv(1024)
            if not response:
                msg = 'StopPrivate ' + client
                P2P_RECEIVER_StopPrivate(msg)
                break
            response_pieces = response.decode().split('\r\n')
            for msg in response_pieces:
                if msg[:12] == 'StopPrivate ':
                    P2P_RECEIVER_StopPrivate(msg)
                    # this would terminate this Thread
                    mySocket_P2P.close()
                    return
                elif msg != '':
                    print(msg)
                    print()
        except:
            continue
    #  In the end, close the connection
    mySocket_P2P.close()
    return


def P2PReceiver(client):

    """
    same functionality as P2P connector.
    for a single Peering, either Connector or Receiver thread being created.

    :param client: the Peer whom you accept the connection request from
    """

    global P2PSocket_listening
    global P2P_contact
    print('[P2P][Receiver-thread] Start P2P with ' + client)
    print()
    P2PconnSocket, addr = P2PSocket_listening.accept()
    P2P_contact[client] = P2PconnSocket
    while True:
        if client not in P2P_contact.keys():
            # tracking whether the Peer is removed or not ( this would terminate this Thread )
            break
        try:
            request = P2PconnSocket.recv(1024)
            if not request:
                msg = 'StopPrivate ' + client
                P2P_RECEIVER_StopPrivate(msg)
                break
            request_list = request.decode().split('\r\n')
            for msg in request_list:
                if msg[:12] == 'StopPrivate ':
                    P2P_RECEIVER_StopPrivate(msg)
                    # this would terminate this Thread
                    break
                elif msg != '':
                    print(msg)
                    print()
        except:
            continue
    #  In the end, close the connection
    P2PconnSocket.close()
    return


#######################################################################################


'''
Peer-to-Peer Section
'''

def P2Plist():
    """
    show the peers
    """
    global P2P_contact
    print('[P2P] list of Peers')
    for peer in P2P_contact.keys():
        print('    '+ peer)
    return


def PreventTimeout():
    """
    prevent Timeout from Server
    """
    global clientSocket
    msgToServer = 'P2Ping\r\n'
    clientSocket.send(msgToServer.encode())
    return


def StartPrivate(command):

    """
    check whether the StartPrivate with Peers is setup or not.
    :param command: the input from terminal
    :param local_client: You
    :return:
    """

    global P2P_contact
    global clientSocket
    global connHolder
    disable = False
    if not connHolder.is_alive():
        disable = True
    try:
        [label,client_to_connect] = command.split()
        if client_to_connect in P2P_contact.keys():
            print('[P2P][Error] You have already set up the P2P connection with ' + client_to_connect)
            print()
        elif not disable:
            print()
            msg = command + '\r\n'
            clientSocket.send(msg.encode())
        elif disable:
            print("[P2P][Notification] Offline Mode from Server cannot initiate the New PrivateMsgService")
            print()
    except:
        print('Invalid Format or Content')
        print()
    return



def PrivateMsg(command, local_client):

    """
    parse the command get each parameters then do the error checking.
    if the Client is your Peer, then send the msg
    :param command: the command you input from terminal
    :param local_client: Your username
    """

    try:
        global P2P_contact
        global connHolder
        [label, target_client, msg] = command.split(' ', 2)
        if local_client == target_client:
            print("[P2P][Error] Bruh, You cannot chat alone")
            print()
        elif target_client in P2P_contact.keys():
            # send the msg to Peer who've startPrivate already
            msgToPeer = '[private] ' + local_client + ' : ' + msg + '\r\n'
            P2P_contact[target_client].send(msgToPeer.encode())
            if StillAlive and connHolder.is_alive():
                PreventTimeout()
        else:
            print("[P2P][Error] Private messaging to " + target_client + " not enabled")
            print()
    except:
        print('[Local] Invalid Format or Content')
        print()
    return

# Peer-to-Peer[Receiver]



def P2P_RECEIVER_StopPrivate(msg):
    """
    Passively received a Peer who stopPrivate msg with you.
    Then Remove that Peer from P2P_contact dictionary
    ( threading point : this would trigger the P2P either connector or Receiver being shutdown )
    :param msg: the msg you received
    """

    global P2P_thread
    global P2P_contact
    [label, Peered_client] = msg.split()
    del P2P_contact[Peered_client]
    print('[P2P][disconnected] ' + Peered_client + ' has stopped the P2P conversation')
    print()
    return


# Peer-to-Peer[Sender]


def P2P_SENDER_StopPrivate(command, local_client,all):
    """
    Actively send a StopPrivate request to the specific Peer
    Then Remove that Peer from P2P_contact dictionary
    ( threading point : this would trigger the P2P either connector or Receiver being shutdown )

    :param command: what u input from terminal
    :param local_client: that's YOU
    """

    global P2P_contact
    global P2P_thread
    global connHolder

    if not all:
        [label, target_client] = command.split()
        if target_client in P2P_contact.keys():
            msg = 'StopPrivate ' + local_client + '\r\n'
            P2P_contact[target_client].send(msg.encode())
            if StillAlive and connHolder.is_alive():
                PreventTimeout()
            del P2P_contact[target_client]
            print('[P2P] disconnected with ' + target_client)
            print()
        else:
            print('[P2P][Error] cannot stopprivate ' + target_client)
    if all:
        for peer in P2P_contact.keys():
            msg = 'StopPrivate ' + local_client + '\r\n'
            P2P_contact[peer].send(msg.encode())
    return


#######################################################################################


'''
Client Section
'''


def ListExtra():
    """
    list extra command
    :return:
    """
    print('listprivate: list of all connected Peers')
    print('exit(): exit the offline mode')
    print('whoami: print your username')
    return



def UserLogoutFromServer(username):
    """
    informing all 'connected' Peers and Server that client is logout
    :param username: local client ( YOU )
    """
    global P2P_thread
    global P2P_contact
    global clientSocket
    clientSocket.send('logout\r\n'.encode())
    return


def WelcomeGraph():
    """
     make terminal looks wholesome :)
    """
    print()
    print(' ' * 10 + '*' * 30)
    print(' ' * 10 + '*' + ' ' * 28 + '*')
    print(' ' * 10 + '*' + ' ' * 5 + 'COMP9331 CHAT ROOM' + ' ' * 5 + '*')
    print(' ' * 10 + '*' + ' ' * 28 + '*')
    print(' ' * 10 + '*' + ' ' * 28 + '*')
    print(' ' * 10 + '*' + ' ' * 8 + 'Produced By' + ' ' * 9 + '*')
    print(' ' * 10 + '*' + ' ' * 2 + 'z5219960 Heng-Chuan Lin' + ' ' * 3 + '*')
    print(' ' * 10 + '*' + ' ' * 28 + '*')
    print(' ' * 10 + '*' * 30)
    print()
    print('Tips: Command should be separated by space e.g. message user text')
    print('Tips: all commands are cast-sensitive ;)')
    print("Tips: type 'extracommand' to get additional function;)")
    return


#######################################################################################

'''
Main Program
'''

# command line argv# for serverName and serverPort

serverName = sys.argv[1]
serverPort = int(sys.argv[2])

# Socket for connecting to Main Server

clientSocket = socket(AF_INET, SOCK_STREAM)
clientSocket.connect((serverName, serverPort))
(myIP, myPort_to_connect_server) = clientSocket.getsockname()

# Socket for listening for P2P msg

P2PSocket_listening = socket(AF_INET, SOCK_STREAM)
P2PSocket_listening.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)

# try to find a available port for creating the listening socket

P2Pport_listening = 1024  # start after well-known port
while True:
    try:
        P2PSocket_listening.bind((myIP, P2Pport_listening))
        P2PSocket_listening.listen(1)
        break
    except:
        P2Pport_listening += 1
        continue

# initial the variable or data

P2P_contact = {}  # storage of the connectSocket from each P2P peer
P2P_thread = {}  # record the thread for each P2P peer

# Login controller
First_Login = False
Login = False
Login_count = 1

# Mode selection

StillAlive = False

print('[Local] Python Client %s %d' % (serverName, serverPort))
print('[Local] Your P2P Port is %d' % P2Pport_listening)

# First while loop for NOT LOGIN stage

while not Login:
    username = input("[Local] Account :   ")
    password = input("[Local] Password:   ")
    login_request = 'LOGIN\r\n' + username + '\r\n' + password + '\r\n'
    try:
        # send the login request to Server through clientSocket
        clientSocket.send(login_request.encode())
        # send timeout for not receiving any response ( just in case, more than 10 clients login )
        clientSocket.settimeout(60)
        # waiting for response and then decoding the msg
        response = clientSocket.recv(1024)
        response_pieces = response.decode().split('\r\n')
        for message in response_pieces:
            # check the content inside msg
            if message == 'LOGIN SUCCESS':
                # trigger A welcoming function and change the login controller
                WelcomeGraph()
                First_Login = True
                Login = True
            elif message == 'LOGIN WRONG':
                # third failure login would terminate the program
                if Login_count == 3:
                    print('[Server][Error] Invalid Password. Your account has been blocked. Please try again later')
                    raise SystemExit
                else:
                    Login_count += 1
                    print('[Server][Error] Invalid Password. Please try again')

            elif message == 'LOGIN BLOCK':
                # get a block info from server then terminate the program
                print('[Server][Error] Your account is blocked due to multiple login failures. Please try again later')
                raise SystemExit
            elif message == 'LOGIN DENIED':
                # get a block info from server then terminate the program
                print('[Server][Error] USER is logged in already')
                raise SystemExit
            elif message == 'LOGIN UNKNOWN':
                # spec didnt specify this part if unknown username.
                print('[Server][Error] UnKnown Username')
            else:
                # print if there's something else
                print(message)

    except SystemExit:
        sys.exit()  # trigger termination of program
    except:
        print('Connection Timeout, Server thread is fulled loaded')
        continue

'''
 After login successfully, 
 A connectionHolder Thread for consecutively get the response from Server would be set.
'''
connHolder = threading.Thread(name="ConnectionHolder", target=ConnectionHolder)
connHolder.daemon = True
connHolder.start()

# from Spec didnt specify timeout from server while doing p2p msg , so I implement this feature
# if Yes, every private command would sent a pkt indicating your doing P2P (w/o conversation context) to server

print('[Local] Woud you want to prevent Timeout from Server while just doing P2P MSG? (Y/N)')
while True:
    print()
    answer = input()
    if answer == 'Y':
        StillAlive = True
        print('[Local] PreventTimeout Enable')
        print()
        break
    elif answer == 'N':
        StillAlive = False
        print('[Local] PreventTimeout Disable')
        print()
        break
    else:
        print('[Local] Cannot identify the answer, just type single Char Y or N')
        print()


# Second while loop for LOGIN stage

while Login:
    try:
        # first login, send the port for P2P msg IP & Port# to Server
        if First_Login:

            First_Login = False
            msg = 'P2P_port ' + myIP + ' ' + str(P2Pport_listening) + '\r\n'
            clientSocket.send(msg.encode())
        # wait for user to input some command
        command = input()
        print()  # keep terminal looks wholesome :)
        # some P2P command is processed w/o Server, hence need to address them locally
        if connHolder.is_alive():
            if command[:13] == 'startprivate ':
                StartPrivate(command)
            elif command[:12] == 'stopprivate ':
                P2P_SENDER_StopPrivate(command, username,False)
            elif command[:8] == 'private ':
                PrivateMsg(command, username)
            elif command == 'logout':
                UserLogoutFromServer(username)
            # filer out input with pressing Enter only
            elif command == 'listprivate':
                P2Plist()
            elif command == 'extracommand':
                ListExtra()
            elif command == 'whoami':
                print('[Local] You are '+ username)
                print()
            elif command != '':
                msg = command + '\r\n'
                clientSocket.send(msg.encode())
        else:
            if command[:13] == 'startprivate ':
                StartPrivate(command)
            elif command[:12] == 'stopprivate ':
                P2P_SENDER_StopPrivate(command, username,False)
            elif command[:8] == 'private ':
                PrivateMsg(command, username)
            elif command == 'listprivate':
                P2Plist()
            elif command == 'extracommand':
                ListExtra()
            elif command == 'whoami':
                print('[Local] You are '+ username)
                print()
            elif command == 'exit()':
                P2P_SENDER_StopPrivate(command,username,True)
                print('See You Next Time ;)')
                print()
                sys.exit()
            else:
                print('[Local] Commands for Private-related commands and exit() available')
                print("[Local] Command 'extracommand' to discover more commands")
                print()
    except ValueError:
        print('Invalid Format or Content')
        print()
