import sys
import os
import threading
import socket
import time
import uuid
import struct
import time
import select
# https://bluesock.org/~willkg/dev/ansi.html
ANSI_RESET = "\u001B[0m"
ANSI_RED = "\u001B[31m"
ANSI_GREEN = "\u001B[32m"
ANSI_YELLOW = "\u001B[33m"
ANSI_BLUE = "\u001B[34m"

_NODE_UUID = str(uuid.uuid4())[:8]


def print_yellow(msg):
    print(f"{ANSI_YELLOW}{msg}{ANSI_RESET}")


def print_blue(msg):
    print(f"{ANSI_BLUE}{msg}{ANSI_RESET}")


def print_red(msg):
    print(f"{ANSI_RED}{msg}{ANSI_RESET}")


def print_green(msg):
    print(f"{ANSI_GREEN}{msg}{ANSI_RESET}")


def get_broadcast_port():
    return 35498


def get_node_uuid():
    return _NODE_UUID


class NeighborInfo(object):
    def __init__(self, delay, last_timestamp, ip=None, tcp_port=None):
        # Ip and port are optional, if you want to store them.
        self.delay = delay
        self.last_timestamp = last_timestamp
        self.ip = ip
        self.tcp_port = tcp_port


############################################
#######  Y  O  U  R     C  O  D  E  ########
############################################


# Don't change any variable's name.
# Use this hashmap to store the information of your neighbor nodes.
neighbor_information = {}
# Leave the server socket as global variable.
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind(('0.0.0.0',0))
server.listen(20)

# Leave broadcaster as a global variable.
broadcaster = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# Setup the UDP socket
broadcaster.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
broadcaster.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
broadcaster.bind(('255.255.255.255',get_broadcast_port()))

def send_broadcast_thread():
    node_uuid = get_node_uuid()
    while True:
        # TODO: write logic for sending broadcasts.
        broadcaster.sendto(f'{node_uuid} ON {server.getsockname()[1]}'.encode('utf-8'),
        ('255.255.255.255', get_broadcast_port()))
        time.sleep(1)   # Leave as is.


def receive_broadcast_thread():
    """
    Receive broadcasts from other nodes,
    launches a thread to connect to new nodes
    and exchange timestamps.
    """
    while True:
        # TODO: write logic for receiving broadcasts.
        data, (ip, port) = broadcaster.recvfrom(4096)
        print_blue(f"RECV: {data} FROM: {ip}:{port}")
        data = data.decode('utf-8').split(' ')
        node, port = data[0], int(data[2])
        if port != server.getsockname()[1]:
            # if not same node
            th1 = daemon_thread_builder(target = exchange_timestamps_thread,args=( node,ip, port)) 
            th1.start()
            tcp_server_thread()

def tcp_server_thread():
    """
    Accept connections from other nodes and send them
    this node's timestamp once they connect.
    """
    th = daemon_thread_builder(target=accept_send_ts)
    th.start()
            
def accept_send_ts():
    while  True:
        conn, add = server.accept()
        print_green('connection accepted')
        timestamp =  time.time()
        packet = struct.pack('!d',timestamp)
        conn.send(packet)
        conn.close()


def exchange_timestamps_thread(other_uuid: str, other_ip: str, other_tcp_port: int):
    """
    Open a connection to the other_ip, other_tcp_port
    and do the steps to exchange timestamps.
    Then update the neighbor_info map using other node's UUID.
    """
    print_yellow(f"ATTEMPTING TO CONNECT TO {other_uuid}")
    try:
        tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp.connect((other_ip,other_tcp_port))
        print_yellow('connection stablished')
        
        packet = tcp.recv(4096)
        time_current = time.time()
        time_previous = struct.unpack('!d',packet)[0]
        print_green(time_previous)
        delay = time_current - time_previous
        tcp.close()
        
        # put in hash table or update if it is in
        if other_uuid in neighbor_information.keys():
            # update
            node_info,broadcast_count = neighbor_information[other_uuid]
            if broadcast_count == 10:
                # reset count and update delay
                broadcast_count = 0
                node_info.delay = delay
                node_info.last_timestamp = time_current
            else:
                broadcast_count += 1
        else:
            # make new object
            node_info = NeighborInfo(delay,time_current,other_ip,other_tcp_port)
            broadcast_count = 0
        neighbor_information.update({other_uuid:(node_info,broadcast_count)})

    except ConnectionRefusedError:
        print_yellow('node is down atm')

def daemon_thread_builder(target, args=()) -> threading.Thread:
    """
    Use this function to make threads. Leave as is.
    """
    th = threading.Thread(target=target, args=args)
    th.setDaemon(True)
    return th



def entrypoint():
    node  = daemon_thread_builder(target=send_broadcast_thread)
    node.start()
    receive_broadcast_thread()

def main():
    """
    Leave as is.
    """
    print("*" * 50)
    print_red("To terminate this program use: CTRL+C")
    print_red("If the program blocks/throws, you have to terminate it manually.")
    print_green(f"NODE UUID: {get_node_uuid()}")
    print("*" * 50)
    time.sleep(2)   # Wait a little bit.
    entrypoint()


if __name__ == "__main__":
    main()
