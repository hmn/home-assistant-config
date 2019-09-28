import socket
import string
import sys


# addressing information of target
IPADDR = '10.254.2.248'
PORTNUM = 4000
# enter the data content of the UDP packet as hex
PACKETDATA = bytes.fromhex('6d6f62696c6504030d0a')
# initialize a socket, think of it as a cable
# SOCK_DGRAM specifies that this is UDP
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)


server_address = (IPADDR, PORTNUM)

try:

    # Send data
    sent = s.sendto(PACKETDATA, server_address)

    # Receive response
    print('waiting to receive')
    data, server = s.recvfrom(4096)
    print('received {!r}'.format(data))

finally:
    print('closing socket')
    s.close()



# connect the socket, think of it as connecting the cable to the address location
#s.connect((IPADDR, PORTNUM))
# send the command
#s.send(PACKETDATA)
# close the socket
#s.close()
