'''
Author:                     z5219960@unsw.edu.au  Heng-Chuan Lin
Python version:             2.7.16   (cannot be executable in python3! use python!)
Function description:       Use iteration to send 10 packent sequencially to the server with UDP.
'''
from socket import *
import sys
import datetime
serverName = sys.argv[1]                            #takes arguments from command line
serverPort = int(sys.argv[2])
rtt_list = []                                       #collecting Round trip times
clientSocket = socket(AF_INET, SOCK_DGRAM)          #create my socket use datagram(UDP)

for i in range(0,10):                                                 #set iteration
    senttime = datetime.datetime.now()                                  #get the sent timestamp
    message = 'PING ' + str(i)+' '+ str(senttime) + ' \r\n'             #packet message
    try:                                                                #if timeout means packet lost
        clientSocket.sendto(message,(serverName, serverPort))           #sent the packet to the server
        clientSocket.settimeout(1)                                      # set the timeout for 1 sec
        modifiedMessage, serverAddress = clientSocket.recvfrom(2048)        #if not receive the error would be triggered -> except
        recvtime = datetime.datetime.now()                                  #get the received time
        delay = recvtime - senttime                                         #calculate the delay
        delay_ms = delay.microseconds/1000                                  #convert to ms
        print('ping to %s, seq = %d, rtt = %d ms' % (serverName,i,delay_ms))        #print information
        rtt_list.append(delay_ms)                                               #collect rtt
    except:
        print('ping to %s, seq = %d, rtt = timeout' % (serverName,i))          # indicate it's dropped
print('min_rtt: %d ms, max_rtt: %d ms, avg_rtt: %d ms'%(min(rtt_list),max(rtt_list),sum(rtt_list)/len(rtt_list))) # print the min, max,avg of rtt