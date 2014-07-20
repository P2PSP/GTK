from __future__ import print_function
import threading
import sys
import socket
import struct
from color import Color
import common
import time

ADDR = 0
PORT = 1

# IP Multicasting Set of Rules
class Peer_IMS(threading.Thread):
    # {{{

    # {{{ Class "constants"

    PLAYER_PORT = 9999          # Port used to serve the player.
    SPLITTER_HOST = "localhost" # Address of the splitter.
    SPLITTER_PORT = 4552        # Port of the splitter.
    TEAM_PORT = 0               # TCP port used to communicate the splitter.

    # }}}

    def print_the_module_name(self):
        # {{{

        sys.stdout.write(Color.yellow)
        print("Peer IMS")
        sys.stdout.write(Color.none)

        # }}}

    def __init__(self):
        # {{{

        threading.Thread.__init__(self)

        print("Running in", end=' ')
        if __debug__:
            print("debug mode")
        else:
            print("release mode")

        self.print_the_module_name()

        print("Player port =", self.PLAYER_PORT)
        #print("Splitter =", sock.getpeername())
        print("Splitter =", self.SPLITTER_HOST)
#        print("Team address =", self.TEAM_HOST)
        print("Team port =", self.TEAM_PORT)

        # {{{ The peer dies if the player disconects.
        # }}}
        self.player_alive = True

        # {{{ The last chunk sent to the player.
        # }}}
        self.played_chunk = 0

        # {{{ The size of the chunk in bytes.
        # }}}
        self.chunk_size = 0

        # {{{ Label the chunks in the buffer as "received" or "not
        # received".
        # }}}
        self.received = []

        # {{{ Counts the number of executions of the recvfrom()
        # function.
        # }}}
        self.recvfrom_counter = 0

        # {{{ "True" while buffering is being performed.
        # }}}
        self.buffering = threading.Event()

        # }}}

    # Tiene pinta de que los tres siguientes metodos pueden simplificarse

    def find_next_chunk(self):
        # {{{

        chunk_number = (self.played_chunk + 1) % common.MAX_CHUNK_NUMBER
        while not self.received[chunk_number % self.buffer_size]:
            chunk_number = (chunk_number + 1) % common.MAX_CHUNK_NUMBER
        return chunk_number

        # }}}

    def play_chunk(self, chunk):
        # {{{

        try:
            self.player_socket.sendall(self.chunks[chunk % self.buffer_size])
        except socket.error, e:
            print(e)
            print('Player disconected, ...', end=' ')
            self.player_alive = False

        # }}}

    def play_next_chunk(self):
        # {{{

        self.played_chunk = self.find_next_chunk()
        self.play_chunk(self.played_chunk)
        self.received[self.played_chunk % self.buffer_size] = False

        # }}}

    def wait_for_the_player(self):
        # {{{ Setup "player_socket" and wait for the player

        self.player_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            # In Windows systems this call doesn't work!
            self.player_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        except Exception, e:
            print (e)
            pass
        self.player_socket.bind(('', self.PLAYER_PORT))
        self.player_socket.listen(0)
        print ("Waiting for the player at", self.player_socket.getsockname())
        self.player_socket = self.player_socket.accept()[0]
        #self.player_socket.setblocking(0)
        print("The player is", self.player_socket.getpeername())

        # }}}

    def connect_to_the_splitter(self):
        # {{{ Setup "splitter" and "splitter_socket"

        # Nota: Ahora no reconvertimos de TCP a UDP!
        
        self.splitter_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.splitter = (self.SPLITTER_HOST, self.SPLITTER_PORT)
        print ("Connecting to the splitter at", self.splitter)
        if self.TEAM_PORT != 0:
            try:
                self.splitter_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            except Exception, e:
                print (e)
                pass
            sys.stdout.write(Color.purple)
            print ("I'm using port the port", self.TEAM_PORT)
            sys.stdout.write(Color.none)
            self.splitter_socket.bind(("", self.TEAM_PORT))
        try:
            self.splitter_socket.connect(self.splitter)
        except Exception, e:
            print(e)
            sys.exit("Sorry. Can't connect to the splitter at " + str(self.splitter))
        print("Connected to the splitter at", self.splitter)
        
        # }}}

    def receive_the_channel(self):
        # {{{
        message = self.splitter_socket.recv(struct.calcsize("4sH"))
        addr, port = struct.unpack("4sH", message)
        addr = socket.inet_ntoa(addr)
        port = socket.ntohs(port)
        channel = (addr, port)
        if __debug__:
            print ("channel =", channel)
        return channel
    
        # }}}

    def receive_and_send_the_header(self):
        # {{{

        header_size_in_bytes = self.header_size_in_chunks * self.chunk_size
        received = 0
        data = ""
        while received < header_size_in_bytes:
            data = self.splitter_socket.recv(header_size_in_bytes - received)
            received += len(data)
            try:
                self.player_socket.sendall(data)
            except Exception, e:
                print (e)
                print ("error sending data to the player")
                print ("len(data) =", len(data))
                time.sleep(1)
            print ("received bytes:", received, "\r", end=" ")

        print ("Received", received, "bytes of header")

        # }}}

    def receive_the_chunk_size(self):
        # {{{

        message = self.splitter_socket.recv(struct.calcsize("H"))
        chunk_size = struct.unpack("H", message)[0]
        self.chunk_size = socket.ntohs(chunk_size)
        print ("chunk_size =", self.chunk_size)
        self.chunk_format_string = "H" + str(self.chunk_size) + "s"

        # }}}

    def receive_the_header_size(self):
        # {{{

        message = self.splitter_socket.recv(struct.calcsize("H"))
        value = struct.unpack("H", message)[0]
        self.header_size_in_chunks = socket.ntohs(value)
        print ("header_size (in chunks) =", self.header_size_in_chunks)

        # }}}

    def receive_the_buffer_size(self):
        # {{{

        message = self.splitter_socket.recv(struct.calcsize("H"))
        buffer_size = struct.unpack("H", message)[0]
        self.buffer_size = socket.ntohs(buffer_size)
        print ("buffer_size =", self.buffer_size)

        # }}}

    def setup_team_socket(self):
        # {{{ Create "team_socket" (UDP) for using the multicast channel

        #self.team_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.team_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        try:
            # In Windows systems this call doesn't work!
            self.team_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        except Exception, e:
            print (e)
            pass
        self.team_socket.bind(('', self.TEAM_PORT))
#        self.team_socket.bind(('', self.SPLITTER_SOCKET.getsockname()[PORT]))

        mreq = struct.pack("4sl", socket.inet_aton(self.MCAST_ADDR), socket.INADDR_ANY)
        self.team_socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        
        # This is the maximum time the peer will wait for a chunk
        # (from the splitter).
        self.team_socket.settimeout(1)

        # }}}

    def receive_a_chunk(self):
        # {{{
        try:
            # {{{ Receive a chunk

            message, sender = self.team_socket.recvfrom(struct.calcsize(self.chunk_format_string))
            self.recvfrom_counter += 1

            # {{{ debug
            if __debug__:
                print (Color.cyan, "Received a message from", sender, \
                    "of length", len(message), Color.none)
            # }}}

            number, chunk = struct.unpack(self.chunk_format_string, message)
            chunk_number = socket.ntohs(number)

            self.chunks[chunk_number % self.buffer_size] = chunk
            self.received[chunk_number % self.buffer_size] = True
            self.numbers[chunk_number % self.buffer_size] = chunk_number # Ojo

            return chunk_number

            # }}}
        except socket.timeout:
            return -2

        # }}}

    def create_the_buffer(self):
        # {{{ The buffer of chunks is a structure that is used to delay
        # the playback of the chunks in order to accommodate the
        # network jittter. Two components are needed: (1) the "chunks"
        # buffer that stores the received chunks and (2) the
        # "received" buffer that stores if a chunk has been received
        # or not. Notice that each peer can use a different
        # buffer_size: the smaller the buffer size, the lower start-up
        # time, the higher chunk-loss ratio. However, for the sake of
        # simpliticy, all peers will use the same buffer size.
        
        self.chunks = [""]*self.buffer_size
        self.received = [False]*self.buffer_size
        self.numbers = [0]*self.buffer_size # Ojo

        # }}}

    def buffer_data(self):
        # {{{ Buffering

        #  Wall time (execution time plus waiting time).
        start_latency = time.time()

        # We will send a chunk to the player when a new chunk is
        # received. Besides, those slots in the buffer that have not been
        # filled by a new chunk will not be send to the player. Moreover,
        # chunks can be delayed an unknown time. This means that (due to the
        # jitter) after chunk X, the chunk X+Y can be received (instead of the
        # chunk X+1). Alike, the chunk X-Y could follow the chunk X. Because
        # we implement the buffer as a circular queue, in order to minimize
        # the probability of a delayed chunk overwrites a new chunk that is
        # waiting for traveling the player, we wil fill only the half of the
        # circular queue.

        print(self.team_socket.getsockname(), "\b: buffering ",)
        sys.stdout.flush()

        # First chunk to be sent to the player.
        chunk_number = self.receive_a_chunk()

        # The receive_and_feed() procedure returns if a packet has been
        # received or if a time-out exception has been arised. In the first
        # case, the returned value is -1 if the packet contains a
        # hello/goodbyte message or a number >= 0 if a chunk has been
        # received. A -2 is returned if a time-out is has happened.
        while chunk_number < 0:
            chunk_number = self.receive_a_chunk()
        self.played_chunk = chunk_number
        print ("First chunk to play", self.played_chunk)

        # Fill up to the half of the buffer
        for x in xrange(self.buffer_size/2):
            print("!", end='')
            sys.stdout.flush()
            while self.receive_a_chunk() < 0:
                pass

        print()
        print('latency =', time.time() - start_latency, 'seconds')
        sys.stdout.flush()

        # }}}

    def keep_the_buffer_full(self):
        # {{{

        # Receive chunks while the buffer is not full
        chunk_number = self.receive_a_chunk()
        while chunk_number < 0:
            chunk_number = self.receive_a_chunk()
        while ((chunk_number - self.played_chunk) % self.buffer_size) < self.buffer_size/2:
            chunk_number = self.receive_a_chunk()
            while chunk_number < 0:
                chunk_number = self.receive_a_chunk()

        # Play the next chunk
        self.play_next_chunk()

        # }}}

    def peers_life(self):
        # {{{

        while self.player_alive:
            self.keep_the_buffer_full()

            if __debug__:
                for i in xrange(self.buffer_size):
                    if self.received[i]:
                        sys.stdout.write(str(i%10))
                    else:
                        sys.stdout.write('.')
                print
                print (self.team_socket.getsockname(),)
                sys.stdout.write(Color.none)

        # }}}

    def run(self):
        # {{{

        self.wait_for_the_player()
        #self.connect_to_the_splitter()
        self.receive_the_chunk_size()
        self.receive_the_header_size()
        self.receive_and_send_the_header()
        self.receive_the_buffer_size()
        #self.receive_the_mcast_channel()
        self.setup_the_team_socket()
        self.splitter_socket.close()
        self.create_the_buffer()
        self.buffer_data()
        self.buffering.set()
        self.buffering = False
        self.peers_life()

        # }}}

    def start(self):
        # {{{

        self.run()

        # }}}

    # }}}
