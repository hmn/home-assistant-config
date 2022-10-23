"""Send command to Siku fan controller.

@see https://www.home-assistant.io/integrations/python_script/
```yaml
service: python_script.fan_control
data:
  ip: 192.168.8.149
  port: 4000
  command: status
  speed: 1
  direction: alternating
  print: all
```
"""
PACKETPREFIX = bytes.fromhex('6d6f62696c65')
PACKETPOSTFIX = bytes.fromhex('0d0a')

def send_command(command: str, ip: str, port: int):
    """Send command to fan controller."""
    PACKETCOMMAND = bytes.fromhex(command)

    # enter the data content of the UDP packet as hex
    #PACKETDATA = bytes.fromhex('6d6f62696c6504010d0a')
    PACKETDATA = PACKETPREFIX + PACKETCOMMAND + PACKETPOSTFIX
    #print(PACKETDATA)

    try:
        # initialize a socket, think of it as a cable
        # SOCK_DGRAM specifies that this is UDP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)
        s.settimeout(10)

        server_address = (ip, port)
        logger.debug('sending "%s" to %s', PACKETDATA, server_address)

        # Send data
        sent = s.sendto(PACKETDATA, server_address)

        # Receive response
        # TODO: add timeout
        #print('waiting to receive')
        data, server = s.recvfrom(4096)

        logger.debug('received "%s" from %s', data, server)
        #print('received {}'.format(data.hex()))
        #print('received {!r}'.format(data))
    except Exception as e:
        raise Exception(f"Error sending command to fan controller: {e}") from e
    finally:
        s.close()

    hexstring = data.hex()
    hexlist = [''.join(x) for x in zip(*[iter(hexstring)]*2)]
    return hexlist


logger.debug('Siku RV fan controller : %s.', data)
ip = data.get('ip')
port = data.get('port', 4000)
command = data.get('command', 'status')
speed = data.get('speed', '01')
direction = data.get('direction', 'alternating')
return_value = data.get('return_value', 'all')
directions = {
    'out': '00',
    'alternating': '01',
    'in': '02'
}
if direction not in directions:
    raise ValueError(f"Invalid direction: {direction}")

# handle commands
status_cmd = '01'
expect_key = None
expect_value = None
if command == 'status':
    cmd = '01'
elif command == 'power':
    cmd = '03'
elif command == 'on':
    cmd = '03'
    expect_key = 7
    expect_value = '01'
elif command == 'off':
    cmd = '03'
    expect_key = 7
    expect_value = '00'
elif command == 'speed':
    cmd = '04' + speed
    expect_key = 19
    expect_value = str(speed)
elif command == 'direction':
    cmd = '06' + directions[direction]
    expect_key = 23
    expect_value = directions[direction]
elif command == 'sleep':
    cmd = '0901'
elif command == 'party':
    cmd = '0902'
else:
    raise ValueError(f"Invalid command: {command}")

try:    
    hexlist = send_command(status_cmd, ip, port)
    if expect_key and hexlist[expect_key] == expect_value:
        # settings already set no need to rerun it
        cmd = None

    if cmd:
        hexlist = send_command(cmd, ip, port)

    power_value = hexlist[7]
    mode_value = hexlist[9]
    speed_value = hexlist[19]
    direction_value = hexlist[23]

    if return_value == 'power':
        print('{}'.format(power_value))
    elif return_value == 'speed':
        print('{}'.format(speed_value))
    elif return_value == 'direction':
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
    raise Exception(f"Error sending command to fan controller: {e}") from e
