#!/usr/bin/python -O
# -*- coding: iso-8859-15 -*-

# This code is distributed under the GNU General Public License (see
# THE_GENERAL_GNU_PUBLIC_LICENSE.txt for extending this information).
# Copyright (C) 2015, the P2PSP team.
# http://www.p2psp.org

from __future__ import print_function
import threading
import sys
import socket
import struct
from color import Color
import common
import time
from _print_ import _print_
from peer_ims import Peer_IMS
from peer_dbs import Peer_DBS
from Crypto.PublicKey import DSA
from Crypto.Hash import SHA256

class Peer_StrpeDs(Peer_DBS):

    def __init__(self, peer):
        sys.stdout.write(Color.yellow)
        _print_("STrPe-DS Peer")
        sys.stdout.write(Color.none)

        threading.Thread.__init__(self)

        self.splitter_socket = peer.splitter_socket
        self.player_socket = peer.player_socket
        self.buffer_size = peer.buffer_size
        self.splitter = peer.splitter
        self.chunk_size = peer.chunk_size
        self.peer_list = peer.peer_list
        self.debt = peer.debt
        self.message_format = peer.message_format
        self.team_socket = peer.team_socket
        self.message_format += '40s40s'
        self.bad_peers = []
        #self.bad_peers.append(('127.0.0.1', 1234))

    def process_message(self, message, sender):
        if self.is_current_message_from_splitter() or self.check_message(message, sender):
            if self.is_control_message(message) and message == 'B':
                self.handle_bad_peers_request()
            else:
                return Peer_DBS.process_message(self, message, sender)
        else:
            self.process_bad_message(message, sender)
            return -1

    def handle_bad_peers_request(self):
        msg = struct.pack("3sH", "bad", len(self.bad_peers))
        self.team_socket.sendto(msg, self.splitter)
        for peer in self.bad_peers:
            msg = socket.inet_aton(peer[0]) + struct.pack('i', peer[1])
            self.team_socket.sendto(msg, self.splitter)

    def check_message(self, message, sender):
        if sender in self.bad_peers:
            return False
        if not self.is_control_message(message):
            chunk_number, chunk, k1, k2 = struct.unpack(self.message_format, message)
            chunk_number = socket.ntohs(chunk_number)
            sign = (self.convert_to_long(k1), self.convert_to_long(k2))
            m = str(chunk_number) + str(chunk) + str(sender)
            return self.dsa_key.verify(SHA256.new(m).digest(), sign)
        return True

    def is_control_message(self, message):
        return len(message) != struct.calcsize(self.message_format)

    def process_bad_message(self, message, sender):
        _print_("bad peer: " + str(sender))
        self.bad_peers.append(sender)
        self.peer_list.remove(sender)

    def unpack_message(self, message):
        # {{{
        chunk_number, chunk, k1, k2 = struct.unpack(self.message_format, message)
        chunk_number = socket.ntohs(chunk_number)
        return chunk_number, chunk
        # }}}

    def receive_dsa_key(self):
        message = self.splitter_socket.recv(struct.calcsize("256s256s256s40s"))
        y, g, p, q = struct.unpack("256s256s256s40s", message)
        y = self.convert_to_long(y)
        g = self.convert_to_long(g)
        p = self.convert_to_long(p)
        q = self.convert_to_long(q)
        self.dsa_key = DSA.construct((y, g, p, q))
        _print_("DSA key received")
        _print_("y = " + str(self.dsa_key.y))
        _print_("g = " + str(self.dsa_key.g))
        _print_("p = " + str(self.dsa_key.p))
        _print_("q = " + str(self.dsa_key.q))

    def convert_to_long(self, s):
        return long(s.rstrip('\x00'), 16)

    def receive_the_next_message(self):
        message, sender = Peer_DBS.receive_the_next_message(self)
        self.current_sender = sender
        return message, sender

    def is_current_message_from_splitter(self):
        return self.current_sender == self.splitter
