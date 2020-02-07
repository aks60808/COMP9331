"""
Python version: python3.7 use python3 command
Author : Lin, Heng-Chuan (z5219960@unsw.edu.au)

description: Server for COMP9331 Assignment
            Support TCP connection and Peer-to-Peer message
"""
from socket import *
import time
import threading
from threading import *
import datetime as dt
import sys

"""
LOGIN/LOGOUT related
"""


def Authentication(login_username, login_password, connectionSocket):
    """

    :param login_username: input value from client's terminal
    :param login_password: input value from client's terminal
    :param connectionSocket: to get the sending address
    :return: Boolean Value
    """
    global clients_online_socket
    global blocktimer
    # intiation
    retval = False
    if login_username in accounts.keys():
        if Debug:
            print(blocklist[login_username])
        # handling multiple login for a single user
        if login_username in clients_online_socket.keys():
            connectionSocket.send('LOGIN DENIED\r\n'.encode())
        # trigger timer if 3-times wrong input
        elif accounts[login_username] == login_password and blocklist[login_username] < 3 and not blocktimer[login_username].is_alive():
            connectionSocket.send('LOGIN SUCCESS\r\n'.encode())
            # record the login time
            server_history_login[login_username] = dt.datetime.now()
            # reset the previous logout history
            server_history_logout[login_username] = None
            retval = True
            blocklist[login_username] = 0
        elif blocklist[login_username] == 2:
            if not blocktimer[login_username].is_alive():
                #set the timer
                blocktimer[login_username] = Timer(block_duration, ReleaseFromBlock, (login_username,))
                blocktimer[login_username].start()
                if Debug:
                    Currtime =TimeNow()
                    print(Currtime+ login_username + ' trigger block')
            connectionSocket.send('LOGIN BLOCK\r\n'.encode())
        else:
            connectionSocket.send('LOGIN WRONG\r\n'.encode())
            blocklist[login_username] += 1
    else:
        connectionSocket.send('LOGIN UNKNOWN\r\n'.encode())

    return retval


def ReleaseFromBlock(user):
    """
    when timer finished, call this function and reset the login counting
    :param user:
    """
    global blocklist
    if Debug:
        Currtime = TimeNow()
        print(Currtime + user + ' is released from block_connection')
    blocklist[user] = 0
    return


def LogOut(client):
    """
    while received 'logout' or trigger timeout, Logout() would be called.

    :param client: client who logout out
    """
    global clients_online_socket
    global server_history_logout
    if Debug:
        Currtime = TimeNow()
        print(Currtime + client + ' LOGOUT')
    # get the connection Socket then send the LOGOUT to client
    connSocket = clients_online_socket[client]
    connSocket.send('LOGOUT\r\n'.encode())
    # delete the recording of that client
    del clients_online_socket[client]
    # store the logout time for whoelsesince service
    server_history_logout[client] = dt.datetime.now()
    # broadcast the logout news to other client (except blocked ones)
    broadcast_msg = '[Server][Notification] ' + str(client) + ' is offline\r\n'
    Notification(client, broadcast_msg)
    return


#####################################################################################################


"""
Server History Section
"""


def WhoelseSinceServer(client_who_asked, segment):
    """
    whoelsesince service, calculate the entire time when srvr've started.
    then do the comparision with input value. if input value is less than that time
    further process the history of each clients.

    :param client_who_asked: sender
    :param segment: content of segment
    """
    global server_history_logout
    global server_history_login
    global accounts
    global clients_online_socket
    try:
        if Debug:
            print(client_who_asked + ' trigger whoelsesince')
            print(server_history_login)
            print(server_history_logout)
        # processing the parameters
        [command, period] = segment[0].split(' ', 1)
        period = int(period)
        CurrTime = dt.datetime.now()
        # get the entire time when server've been build
        interval = CurrTime - server_history_login['server']
        # send to msg to client
        connSocket = clients_online_socket[client_who_asked]
        msg = '[Server] Whoelsesince ' + str(period) + ' seconds blow\r\n'
        connSocket.send(msg.encode())
        # list all login user who login after server started if input sec > entire time when server've been build
        if interval < dt.timedelta(seconds=period):
            for client in server_history_login.keys():
                if client != 'server' and server_history_login[client] is not None and client_who_asked != client:
                    msg = '    ' + client + '\r\n'
                    connSocket.send(msg.encode())
        else:
            # check the each clients
            for client in accounts.keys():
                if client != client_who_asked:  # exclude you
                    # clients who still online
                    if server_history_login[client] is not None and server_history_logout[client] is None:
                        msg = '    ' + client + '\r\n'
                        connSocket.send(msg.encode())
                    # clients who've logout already
                    elif server_history_login[client] is not None and server_history_logout[client] is not None:
                        value_login = CurrTime - server_history_login[client]
                        value_logout = CurrTime - server_history_logout[client]
                        # if any value < input sec then send the name of that specific client
                        if value_login < dt.timedelta(seconds=period) or value_logout < dt.timedelta(seconds=period):
                            msg = '    ' + client + '\r\n'
                            connSocket.send(msg.encode())
    except:
        if Debug:
            print('error of whoelsesince')
        InvalidContent(client_who_asked)
    return


def WhoelseService(user):
    """
    Check whoelse is online as well.
    :param user: client who request a whoelse service
    """
    try:
        global clients_online_socket
        if Debug:
            Currtime = TimeNow()
            server_info = Currtime + user + ' is asking whoelse'
            print(server_info)
        connSocket = clients_online_socket[user]
        # if there's only 1 client, basically just you
        if len(clients_online_socket.keys()) == 1:
            connSocket.send('[Server] No one except you \r\n'.encode())
        # if > 1, just list them all
        else:
            connSocket.send('[Server] Clients Online  \r\n'.encode())
            for client in clients_online_socket.keys():
                if client != user:
                    msg = '    ' + client + '\r\n'
                    connSocket.send(msg.encode())
    except:
        InvalidContent(user)
    return


#####################################################################################################


"""
Message Section
"""


def MsgService(sender, segments):
    """
    A function handling Forwarding and Offline Msg.
    :param sender:  who send this request
    :param segments:  content of request
    """
    global clients_online_socket
    global offline_data
    global accounts
    try:
        # processing each parameters
        segments = segments[0].split(' ', 2)
        receiver = segments[1]
        content = segments[2]
        connSocket = clients_online_socket[sender]
        # identify the receiver
        if receiver in accounts.keys():
            # check whether sender is blocked from receiver or not
            if UserGetBlockedFrom(sender, receiver):
                msg = '[Server] Your message could not be delivered as the recipient has blocked you\r\n'
                connSocket.send(msg.encode())
            # if receiver is online  -> call Forwarding
            elif receiver in clients_online_socket.keys():
                if receiver == sender:
                    msg = '[Server][Error] Do not send msg to yourself\r\n'
                    clients_online_socket[sender].send(msg.encode())
                else:
                    msg = '[Live] ' + sender + ': ' + content + '\r\n'
                    MsgForwarding(receiver, msg)
            # if receiver is offline  -> preserve the msg into Offline storage of receiver
            else:
                msg = '[Offline] ' + sender + ': ' + content + '\r\n'
                feedback = '[Server] ' + receiver + ' is currently Offline. msg would be preserved in his offline_msg\r\n'
                connSocket.send(feedback.encode())
                offline_data[receiver].append(msg)
        else:
            msg = '[Server][Error] ' + receiver + ' cannot be identified\r\n'
            connSocket.send(msg.encode())
    except:
        InvalidContent(sender)
    return


def MsgOffline(client):
    """
    send the msg store from offline_data to the sender (in order)
    :param client: server would send msg to
    """
    global clients_online_socket
    global offline_data
    connSocket = clients_online_socket[client]
    # if some msg there
    if offline_data[client]:
        connSocket.send('[Server] You have Offline messages\r\n'.encode())
        for msg in offline_data[client]:
            connSocket.send(msg.encode())
        # clear the offline_data
        offline_data[client] = []
        if Debug:
            Currtime = TimeNow()
            print(Currtime + client + " trigger offline msg delivery")
    return


def MsgForwarding(receiver, msg):
    """
    Forward the msg to the reciever
    :param receiver: server send to
    :param msg: text from sender ( processing into msg already)
    """
    global clients_online_socket
    if Debug:
        Currtime = TimeNow()
        print(Currtime + msg + ' forwarding to ' + receiver)
    connSocket = clients_online_socket[receiver]
    connSocket.send(msg.encode())
    return


#####################################################################################################

"""
Broadcast Section
"""


def Notification(user, text):
    """
    This function is for broadcasting login/logout of clients
    :param user: client name
    :param text: string you put into this function
    """
    global clients_online_socket
    for client in clients_online_socket.keys():
        # avoid send to himself and clients in blacklist
        if client != user and not UserGetBlockedFrom(client, user):
            client_connSocket = clients_online_socket[client]
            client_connSocket.send(text.encode())
    return


def BroadcastService(client_who_broadcast, segments):
    """
    broadcast the msg for clients. if someone block that client, server should inform that client.
    :param client_who_broadcast:  server received broadcast request from
    :param segments: content of msg
    """
    global clients_online_socket
    # initiation
    beBlock = False
    try:
        if Debug:
            Currtime = TimeNow()
            print(Currtime + client_who_broadcast + " use the broadcast service ")
        # processing the segments
        text = segments[0].split(' ', 1)[1]
        msg = '[broadcast] ' + client_who_broadcast + ' : ' + text + '\r\n'
        for client in clients_online_socket.keys():
            # dont broadcast to that client
            if client != client_who_broadcast:
                # check anyone who block that client
                if client_who_broadcast in blacklist[client]:
                    beBlock = True
                else:
                    connSocket = clients_online_socket[client]
                    connSocket.send(msg.encode())
        if beBlock:
            # send the feedback if someone block that client
            connSocket = clients_online_socket[client_who_broadcast]
            msg = '[Server] Your message could not be delivered to some recipients\r\n'
            connSocket.send(msg.encode())
    except:
        InvalidContent(client_who_broadcast)
    return


#####################################################################################################


"""
Blacklist Section
"""


def BlackListService(client, segments, block):
    """

    :param client: who send the request
    :param segments: content of request
    :param block: boolean, True for Block command, False for unBlock command
    """
    global clients_online_socket
    global accounts
    [command, blocked_client] = segments[0].split(' ', 1)
    connSocket = clients_online_socket[client]
    # identify the target client
    if blocked_client in accounts.keys() and client != blocked_client:
        # command with block
        if block:
            # add to list if not in blacklist
            if blocked_client not in blacklist[client]:
                blacklist[client].append(blocked_client)
                msg = '[Server] ' + blocked_client + ' is now added to your blacklist :' \
                      + str(blacklist[client]) + '\r\n'
                connSocket.send(msg.encode())
            else:
                msg = '[Server][Error] ' + blocked_client + ' is already in your blacklist :' \
                      + str(blacklist[client]) + '\r\n'
                connSocket.send(msg.encode())
        # command with unblock
        if not block:
            # remove from list if in blacklist
            if blocked_client in blacklist[client]:
                blacklist[client].remove(blocked_client)
                msg = '[Server] ' + blocked_client + ' is now removed from your blacklist: ' \
                      + str(blacklist[client]) + '\r\n'
                connSocket.send(msg.encode())
            else:
                msg = '[Server][Error] ' + blocked_client + " isn't in your blacklist: " \
                      + str(blacklist[client]) + '\r\n'
                connSocket.send(msg.encode())
    # some error-handling
    elif blocked_client == client:
        msg = '[Server][Error] Bruh, You cannot block yourself\r\n'
        connSocket.send(msg.encode())
    # target client cannot be identified
    else:
        msg = '[Server][Error] ' + blocked_client + ' cannot be identified\r\n'
        connSocket.send(msg.encode())
    return


def UserGetBlockedFrom(blocked_client, client):
    """
    check whether this {blocked_client} is in {client}'s blacklist or not
    :return: boolean
    """
    global blacklist
    result = False
    if blocked_client in blacklist[client]:
        result = True
    return result


#####################################################################################################


"""
Other Function Section
"""


def StartPrivateService(client, segment):
    """
    managing the Startprivate request from clients
    :param client: who send the request
    :param segment: content of request
    """
    global clients_online_socket
    global accounts
    connSocket = clients_online_socket[client]
    try:
        [command, target_client] = segment[0].split()
        # some error-hanlding
        if target_client == '':
            InvalidContent(client)
        # unidentified client
        elif target_client not in accounts.keys():
            msg = "[Server][Error] Cannot identify the User : " + target_client + "\r\n"
            connSocket.send(msg.encode())
        # client in blacklist
        elif UserGetBlockedFrom(client, target_client):
            msg = "[Server][Error] You've been blocked by " + target_client + "\r\n"
            connSocket.send(msg.encode())
        # invalid client handling
        elif client == target_client:
            connSocket.send("[Server][Error] Bruh, it cannot be yourself\r\n".encode())
        # client currently offline
        elif target_client not in clients_online_socket.keys():
            msg = "[Server][Error] " + target_client + " is currently offline\r\n"
            connSocket.send(msg.encode())
        else:
            # extract the IP and Port info of targer_client, then send to the client
            (IP, port) = clients_online_P2P[target_client]
            # send feedback
            client_feedback = 'Ini_P2P_connect ' + ' ' + target_client + ' ' + IP + " " + str(port) + '\r\n'
            connSocket.send(client_feedback.encode())
            # send listening request of the client to target_client
            target_client_connSocket = clients_online_socket[target_client]
            target_client_info = 'Ini_P2P_listen ' + client + '\r\n'
            target_client_connSocket.send(target_client_info.encode())
    except:
        InvalidContent(client)
    return


def TimeNow():
    """
    get the Time string for Debugging
    """
    return '[' + str(dt.datetime.now()) + '] '


def InvalidCommand(client):
    """
    ease of doing Error-shooting
    :param client: client_to_send
    """
    global clients_online_socket
    connSocket = clients_online_socket[client]
    connSocket.send('[Server][Error] InValid COMMAND\r\n'.encode())
    return


def InvalidContent(client):
    """
    ease of doing Error-shooting
    :param client: client_to_send
    """
    global clients_online_socket
    connSocket = clients_online_socket[client]
    connSocket.send('[Server][Error] InValid Content or Format\r\n'.encode())
    return


#####################################################################################################

"""
Thread Function Section 
"""


def Recv_handler(n):
    global accounts
    global serverSocket
    global clients_online_socket
    global blocklist
    if Debug:
        Currtime = TimeNow()
        print(Currtime + 'Thread%d is ready for service' % n)
    connectionSocket, addr = serverSocket.accept()
    # initiation
    Login_status = False
    First_Login = False
    username = None
    while True:
        try:
            if Login_status:
                # if first login -> server send welcome msg and the offline msg to client.
                if First_Login:
                    welcome_msg = '[Server] Welcome ' + username + ' \r\n'
                    connectionSocket.send(welcome_msg.encode())
                    MsgOffline(username)
                    First_Login = False
                # since login, now we can set the timeout function
                connectionSocket.settimeout(timeout_value)
            # listening for request
            request = connectionSocket.recv(1024)
            # if request keep sending blank pkt, terminate this thread
            if not request:
                break
            if Debug:
                Currtime = TimeNow()
                print(Currtime + 'thread' + str(n) + ' packet received : ' + request.decode() + ' from ' + str(addr))
            segments = request.decode().split('\r\n')
            if segments[0] == 'LOGIN':
                username = segments[1]
                pwd = segments[2]
                if Authentication(username, pwd, connectionSocket):
                    # mapping the connSocket to the client
                    clients_online_socket[username] = connectionSocket
                    Login_status = True
                    First_Login = True
                    if Debug:
                        Currtime = TimeNow()
                        print(Currtime + username + ' LOGIN')
                    # set up the broadcast text and broadcast the notification
                    broadcast_msg = '[Server][Notification] ' + str(username) + ' is online now\r\n'
                    Notification(username, broadcast_msg)
            # other just handling different kinds of requests
            elif segments[0][:9] == 'P2P_port ':
                [label, clientIP, clientP2Pport] = segments[0].split()
                clients_online_P2P[username] = (clientIP, clientP2Pport)
            elif segments[0][:8] == 'message ':
                MsgService(username, segments)
            elif segments[0][:10] == 'broadcast ':
                BroadcastService(username, segments)
            elif segments[0] == 'whoelse':
                WhoelseService(username)
            elif segments[0][:13] == 'whoelsesince ':
                WhoelseSinceServer(username, segments)
            elif segments[0] == 'logout':
                LogOut(username)
                # if logout terminate this thread function
                break
            elif segments[0][:6] == "block ":
                BlackListService(username, segments, True)
            elif segments[0][:8] == "unblock ":
                BlackListService(username, segments, False)
            elif segments[0][:13] == "startprivate ":
                StartPrivateService(username, segments)
            elif segments[0] == 'P2Ping':
                # this just no operation - avoiding from timeout occured
                pass
            else:
                InvalidCommand(username)
        except:
            if Debug:
                print('session expired log ' + username + ' out!!')
            # Timeout -> inform that client then log that client out
            timeout_info = '[Server][Timeout] standing idle for ' + str(timeout_value) + ' sec\r\n'
            connectionSocket.send(timeout_info.encode())
            LogOut(username)
            # terminate this thread function
            break
    # this prevent some naughty client use ctrl + c rahter than typing logout command
    if username in clients_online_socket.keys() and Login_status:
        LogOut(username)
    elif username in accounts.keys() and not Login_status and not blocktimer[username].is_alive():
        if Debug:
            print('blocklist of ' + username + ' has been reset')
        blocklist[username] = 0
    # close the TCP connection
    connectionSocket.close()
    if Debug:
        Currtime = TimeNow()
        print(Currtime + 'Thread%d is closed' % n)
    # sleep a bit ensuring everything works fine
    time.sleep(0.1)
    return


#####################################################################################################


"""
Main() Section
"""


# setup Debug mode

Debug = False

# Server setup

serverName = 'localhost'
serverPort = int(sys.argv[1])
block_duration = int(sys.argv[2])
timeout_value = int(sys.argv[3])

# Data storage
accounts = {}  # record the accounts and pwd from credentials.txt
clients_online_P2P = {}  # record their P2P port
clients_online_socket = {}  # record their connSocket
offline_data = {}  # store offline msg
blocklist = {}  # blocklist for login counting
blocktimer={}
blacklist = {}  # blacklist for recording blocked-client
server_history_login = {}  # login_record
server_history_logout = {}  # logout_record
threadlist = [] # this handling the threads

file = open('credentials.txt')
# processing the data and then do some initiation
for i in file.readlines():
    i = i.rstrip()
    username, password = i.split()
    accounts[username] = password
    blocklist[username] = 0
    blocktimer[username] = Timer(block_duration, ReleaseFromBlock, (username,))
    offline_data[username] = []
    blacklist[username] = []
    server_history_login[username] = None
    server_history_logout[username] = None

#ServerSocket setup
serverSocket = socket(AF_INET, SOCK_STREAM)
serverSocket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
serverSocket.bind((serverName, serverPort))
serverSocket.listen(1)
server_history_login['server'] = dt.datetime.now()  # record the initial time


if Debug:
    print(accounts.keys())
# initial ten threads available
for num in range(0, 10):
    threadlist.append(threading.Thread(name="RecvHandler", target=Recv_handler, args=(num + 1,)))
    threadlist[num].daemon = True
    threadlist[num].start()
while True:
    time.sleep(1)
    for i in range(len(threadlist)):
        # if thread is finished (i.e. disconnection), revive it for serving next client
        if not threadlist[i].is_alive():
            threadlist[i] = threading.Thread(name="RecvHandler", target=Recv_handler, args=(i + 1,))
            threadlist[i].daemon = True
            threadlist[i].start()
