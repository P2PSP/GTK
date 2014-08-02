#!/usr/bin/python -O
# -*- coding: iso-8859-15 -*-

# This code is distributed under the GNU General Public License (see
# THE_GENERAL_GNU_PUBLIC_LICENSE.txt for extending this information).

# Copyright (C) 2014, the P2PSP team.

# {{{ Imports

from __future__ import print_function
import sys
import socket
import struct
import time
import argparse
from color import Color
import threading
from lossy_socket import lossy_socket
import common
from _print_ import _print_

from peer_ims import Peer_IMS
from peer_dbs import Peer_DBS
from peer_fns import Peer_FNS
from monitor_fns import Monitor_FNS
from peer_lossy import Peer_Lossy
from monitor_lrs import Monitor_LRS
from lossy_peer import Lossy_Peer

# }}}

# Some useful definitions.
ADDR = 0
PORT = 1

class Peer():

    def __init__(self):
    
        # {{{ Args handling and object instantiation
        parser = argparse.ArgumentParser(description='This is the peer node of a P2PSP team.')

        parser.add_argument('--chunk_loss_period', help='0 -> no chunk loss, 1 -> lost all chunks, 2, lost half of the chunks ... Default = {}'.format(Lossy_Peer.CHUNK_LOSS_PERIOD))

        parser.add_argument('--max_chunk_debt', help=' ({})'.format(Peer_DBS.MAX_CHUNK_DEBT))

        parser.add_argument('--player_port', help='Port to communicate with the player. ({})'.format(Peer_IMS.PLAYER_PORT))

        parser.add_argument('--splitter_host', help='IP address or host name of the splitter. Default = {}.'.format(Peer_IMS.SPLITTER_HOST))

        parser.add_argument('--splitter_port', help='Listening port of the splitter. Default = {}.'.format(Peer_IMS.SPLITTER_PORT))

        parser.add_argument('--team_port', help='Port to communicate with the peers. Default {} (the SO will chose it).'.format(Peer_IMS.TEAM_PORT))

        args = parser.parse_known_args()[0]

        if args.splitter_host:
            Peer_IMS.SPLITTER_HOST = socket.gethostbyname(args.splitter_host)
            print ('SPLITTER_HOST =', Peer_IMS.SPLITTER_HOST)

        if args.splitter_port:
            Peer_IMS.SPLITTER_PORT = int(args.splitter_port)
            print ('SPLITTER_PORT =', Peer_IMS.SPLITTER_PORT)

        if args.team_port:
            Peer_IMS.TEAM_PORT = int(args.team_port)
            print ('TEAM_PORT =', Peer_IMS.TEAM_PORT)

        if args.player_port:
            Peer_IMS.PLAYER_PORT = int(args.player_port)
            print ('PLAYER_PORT =', Peer_IMS.PLAYER_PORT)

        peer = Peer_IMS()
        peer.player_connection.wait()
        peer.connect_to_the_splitter()
        mcast_endpoint = peer.receive_the_mcast_endpoint()
        _print_("Multicast end-point =", mcast_endpoint)
        
        # A mcast_endpoint is always received, even for DBS peers.
        if mcast_endpoint[ADDR] == '0.0.0.0':
            # {{{ This is a "unicast" peer.

            if Monitor_DBS.are_you_a_monitor():
                peer = Monitor_DBS()
    #            peer = Monitor_LRS()
            else:
                if args.chunk_loss_period:
                    Peer_DBS.CHUNK_LOSS_PERIOD = int(args.chunk_loss_period)
                    print ('CHUNK_LOSS_PERIOD =', Peer_DBS.CHUNK_LOSS_PERIOD)
                    if int(args.chunk_loss_period) != 0:
                        peer = Lossy_Peer()
                    else:
                        peer = Peer_DBS()
                else:
                    peer = Peer_DBS()
            #        peer = Peer_FNS()

            # }}}
        else:
            # {{{ This is a "multicast" peer.
            pass
            #peer.start()
            #peer = Peer_IMS(sock, channel)
            #print ("---->", Peer_IMS.SPLITTER_SOCKET)

            # }}}

        # }}}

        # {{{ Run!

        peer.configure()
        peer.disconnect_from_the_splitter()
        peer.buffer_data()
        peer.start()
        #peer.buffering.wait()

        print("+-----------------------------------------------------+")
        print("| Received = Received kbps, including retransmissions |")
        print("|     Sent = Sent kbps                                |")
        print("|       (Expected values are between parenthesis)     |")
        print("------------------------------------------------------+")
        print()
        print("    Time |        Received |             Sent | Team description")
        print("---------+-----------------+------------------+-----------------")

        last_chunk_number = peer.played_chunk
        if hasattr(peer, 'sendto_counter'):
            last_sendto_counter = 0#peer.sendto_counter
        else:
            peer.sendto_counter = 0
            last_sendto_counter = 0
        if not hasattr(peer, 'peer_list'):
            peer.peer_list = []
        last_recvfrom_counter = peer.recvfrom_counter
        while peer.player_alive:
            time.sleep(1)
            kbps_expected_recv = ((peer.played_chunk - last_chunk_number) * peer.chunk_size * 8) / 1000
            last_chunk_number = peer.played_chunk
            kbps_recvfrom = ((peer.recvfrom_counter - last_recvfrom_counter) * peer.chunk_size * 8) / 1000
            last_recvfrom_counter = peer.recvfrom_counter
            team_ratio = len(peer.peer_list) /(len(peer.peer_list) + 1.0)
            kbps_expected_sent = int(kbps_expected_recv*team_ratio)
            kbps_sendto = ((peer.sendto_counter - last_sendto_counter) * peer.chunk_size * 8) / 1000
            last_sendto_counter = peer.sendto_counter
            if kbps_recvfrom > 0:
                nice = 100.0/float((float(kbps_expected_recv)/kbps_recvfrom)*(len(peer.peer_list)+1))
            else:
                nice = 0.0
    #        print(1.0/float(nice))
            #print ("Played chunk = ", peer.played_chunk)
            if kbps_expected_recv < kbps_recvfrom:
                sys.stdout.write(Color.red)
            elif kbps_expected_recv > kbps_recvfrom:
                sys.stdout.write(Color.green)
            _print_("|" + repr(kbps_expected_recv).rjust(8), end=Color.none)
            print(('(' + repr(kbps_recvfrom) + ')').rjust(8), end=' | ')
            #print(("{:.1f}".format(nice)).rjust(6), end=' | ')
            #sys.stdout.write(Color.none)
            if kbps_expected_sent > kbps_sendto:
                sys.stdout.write(Color.red)
            elif kbps_expected_sent < kbps_sendto:
                sys.stdout.write(Color.green)
            print(repr(kbps_sendto).rjust(8), end=Color.none)
            print(('(' + repr(kbps_expected_sent) + ')').rjust(8), end=' | ')
            #sys.stdout.write(Color.none)
            #print(repr(nice).ljust(1)[:6], end=' ')
            print(len(peer.peer_list), end=' ')
            counter = 0
            for p in peer.peer_list:
                if (counter < 5):
                    print(p, end=' ')
                    counter += 1
                else:
                    break
            print()

            # }}}

x = Peer()

