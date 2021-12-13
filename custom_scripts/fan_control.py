import socket
import string
import sys
import argparse

def send_command(value):
    """Send command to fan controller."""
    PACKETCOMMAND = bytes.fromhex(value)

    # enter the data content of the UDP packet as hex
    #PACKETDATA = bytes.fromhex('6d6f62696c6504010d0a')
    PACKETDATA = PACKETPREFIX + PACKETCOMMAND + PACKETPOSTFIX
    #print(PACKETDATA)

    try:
        # initialize a socket, think of it as a cable
        # SOCK_DGRAM specifies that this is UDP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)
        s.settimeout(10)

        server_address = (IPADDR, PORTNUM)
        #print(server_address)

        # Send data
        sent = s.sendto(PACKETDATA, server_address)

        # Receive response
        # TODO: add timeout
        #print('waiting to receive')
        data, server = s.recvfrom(4096)

        #print('received {}'.format(data.hex()))
        #print('received {!r}'.format(data))
    except Exception as e:
        raise Exception(f"Error sending command to fan controller: {e}") from e
    finally:
        #print('closing socket')
        s.close()

    hexstring = data.hex()
    hexlist = [''.join(x) for x in zip(*[iter(hexstring)]*2)]
    return hexlist


parser = argparse.ArgumentParser(description='Siku RV fan controller.')
parser.add_argument('--ip', help='fan ip addreee', required=True)
parser.add_argument('--port', help='fan UDP port (default: 4000)', default=4000)
parser.add_argument('--command', help='command to run',
                    choices=['status', 'power', 'speed', 'direction', 'sleep', 'party', 'on', 'off'],
                    required=True)
parser.add_argument('--speed', help='speed to use',
                    choices=['01', '02', '03'],
                    default='01')
parser.add_argument('--direction', help='airflow direction',
                    choices=['out', 'alternating', 'in'],
                    default='alternating')
parser.add_argument('--print', help='what value to return',
                    choices=['all', 'power', 'speed', 'direction'],
                    default='all')

args = parser.parse_args()

#print(args)

# addressing information of target
IPADDR = args.ip
PORTNUM = args.port
PACKETPREFIX = bytes.fromhex('6d6f62696c65')
PACKETPOSTFIX = bytes.fromhex('0d0a')
directions = {
    'out': '00',
    'alternating': '01',
    'in': '02'
}

# handle commands
if args.command == 'status':
    cmd = '01'
elif args.command == 'power':
    cmd = '03'
elif args.command == 'on':
    cmd = '03'
    status_cmd = '01'
    status_expect = '00'
elif args.command == 'off':
    cmd = '03'
    status_cmd = '01'
    status_expect = '01'
elif args.command == 'speed':
    cmd = '04' + args.speed
elif args.command == 'direction':
    cmd = '06' + directions[args.direction]
elif args.command == 'sleep':
    cmd = '0901'
elif args.command == 'party':
    cmd = '0902'
else:
    print('invalid command')
    exit(1)

try:
    if status_cmd:
        hexlist = send_command(status_cmd)
        if hexlist[7] == status_expect:
            # fan already on/off no need to run command
            print(hexlist[7])
            exit(0)

    hexlist = send_command(cmd)

    power_value = hexlist[7]
    mode_value = hexlist[9]
    speed_value = hexlist[19]
    direction_value = hexlist[23]

    if args.print == 'power':
        print('{}'.format(power_value))
    elif args.print == 'speed':
        print('{}'.format(speed_value))
    elif args.print == 'direction':
        for key, value in directions.items():
            if value == direction_value:
                print('{}'.format(key))
                continue
    else:
        print('power     : {}'.format(power_value))
        print('mode      : {}'.format(mode_value))
        print('speed     : {}'.format(speed_value))
        print('direction : {}'.format(direction_value))
except Exception as e:
    print("Error : {}".format(e))
    exit(1)
