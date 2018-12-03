#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2010  Nathanael C. Fritz
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

import sys, time, datetime, string, random
import logging
import getpass
import threading
#from optparse import OptionParser
import argparse
import sleekxmpp
from sleekxmpp.exceptions import IqError
from sleekxmpp.xmlstream import ElementBase
from xml.etree import cElementTree as ET

from atomiclong import AtomicLong
from ofrestapi.muc import Muc

# Python versions before 3.0 do not use UTF-8 encoding
# by default. To ensure that Unicode is handled properly
# throughout SleekXMPP, we will set the default encoding
# ourselves to UTF-8.
if sys.version_info < (3, 0):
    from sleekxmpp.util.misc_ops import setdefaultencoding
    setdefaultencoding('utf8')
else:
    raw_input = input

g_result = [0, 0]  #success, total number
g_ready = AtomicLong(0)

#xmpp_domain = "jitsi-meet-charles.magnet.com"
#openfire_nodes = [
#       "http://charles-openfire-1.magnet.com:9090",
#        "http://charles-openfire-2.magnet.com:9090" ]
#openfire_shared_key = "Lz4vLf3yE7FrPWGm"

# by default, using random room name every time
room_name = ""
xmpp_domain = "nuancejitsi.magnet.com"
openfire_nodes = [
    "http://nuancejitsi-openfire-1.magnet.com:9090", 
    "http://nuancejitsi-openfire-2.magnet.com:9090" ]

openfire_shared_key = "C27RXhWKFw5dvAHT"

class XMPPThread(threading.Thread):
    def __init__(self, xmpp):
        threading.Thread.__init__(self)
        self.xmpp = xmpp

    def run(self):
        # Connect to the XMPP server and start processing XMPP stanzas.
        if self.xmpp.connect():
            self.xmpp.process(block=True)
            #print("Done")
        else:
            print("Unable to connect.")

def check_clusters(roomname):

    global openfire_nodes, openfire_shared_key
    if len (openfire_nodes) <= 0:
        print("Need cluster node > 0")
        return False
  
    mucs = []
    roomss = []
    for node in openfire_nodes:
        muc = Muc(node, openfire_shared_key)
        # possible exception here
        rooms = muc.get_rooms()
        mucs.append(muc)
        roomss.append(rooms)
        #print(rooms)

    if len(roomss) == len(openfire_nodes) and \
        all(v == roomss[0] for v in roomss):
        occs = []
        for muc in mucs:
            # possible exception here
            oc = muc.get_room_occupants(roomname)
            occs.append(oc)

        if len(occs) == len(openfire_nodes) and \
            all(len(occ['occupants']) == 2 and occ == occs[0] for occ in occs):
            return True
        else:
            print("occupants do not match or the count of occupants is not correct")
            i = 0
            for occ in occs:
                print("node{}: occ#: {} {}".format(i, len(occ['occupants']), occ))
                i += 1
            return False
    else:
        print("rooms do not match")
        i = 0
        for rooms in roomss:
            print("node{}: {}".format(i, rooms))
            i += 1
        return False

class MUCBot(sleekxmpp.ClientXMPP):

    """
    A simple SleekXMPP bot that will greets those
    who enter the room, and acknowledge any messages
    that mentions the bot's nickname.
    """

    def __init__(self, jid, password, room, nick, owner=False):
        sleekxmpp.ClientXMPP.__init__(self, jid, password)

        self.room = room
        self.nick = nick
        self.owner = owner

        # The session_start event will be triggered when
        # the bot establishes its connection with the server
        # and the XML streams are ready for use. We want to
        # listen for this event so that we we can initialize
        # our roster.
        self.add_event_handler("session_start", self.start)

        # The groupchat_message event is triggered whenever a message
        # stanza is received from any chat room. If you also also
        # register a handler for the 'message' event, MUC messages
        # will be processed by both handlers.
        self.add_event_handler("groupchat_message", self.muc_message)

        # The groupchat_presence event is triggered whenever a
        # presence stanza is received from any chat room, including
        # any presences you send yourself. To limit event handling
        # to a single room, use the events muc::room@server::presence,
        # muc::room@server::got_online, or muc::room@server::got_offline.
        self.add_event_handler("muc::%s::got_online" % self.room,
                               self.muc_online)


    def start(self, event):
        """
        Process the session_start event.

        Typical actions for the session_start event are
        requesting the roster and broadcasting an initial
        presence stanza.

        Arguments:
            event -- An empty dictionary. The session_start
                     event does not provide any additional
                     data.
        """
        self.get_roster()
        self.send_presence()
        self.plugin['xep_0045'].joinMUC(self.room,
                                        self.nick,
                                        # If a room password is needed, use:
                                        # password=the_room_password,
                                        wait=True)

    def muc_message(self, msg):
        """
        Process incoming message stanzas from any chat room. Be aware
        that if you also have any handlers for the 'message' event,
        message stanzas may be processed by both handlers, so check
        the 'type' attribute when using a 'message' event handler.

        Whenever the bot's nickname is mentioned, respond to
        the message.

        IMPORTANT: Always check that a message is not from yourself,
                   otherwise you will create an infinite loop responding
                   to your own messages.

        This handler will reply to messages that mention
        the bot's nickname.

        Arguments:
            msg -- The received message stanza. See the documentation
                   for stanza objects and the Message stanza to see
                   how it may be used.
        """
        """
        if msg['mucnick'] != self.nick and self.nick in msg['body']:
            self.send_message(mto=msg['from'].bare,
                              mbody="I heard that, %s." % msg['mucnick'],
                              mtype='groupchat')
        """

    def unlock_room(self):
        query = ET.Element('{http://jabber.org/protocol/muc#owner}query')
        x = ET.Element('{jabber:x:data}x', type='submit')
        query.append(x)
        #print("!!!!!Charles !!!! room name: {}".format(self.room))
        iq = self.make_iq_set(sub=query, ito=self.room)
        try:
            iq.send(timeout=60)
            ret = True
        except IqError as e:
            print(e)
            ret = False
        return ret

    def muc_online(self, presence):
        """
        Process a presence stanza from a chat room. In this case,
        presences from users that have just come online are
        handled by sending a welcome message that includes
        the user's nickname and role in the room.

        Arguments:
            presence -- The received presence stanza. See the
                        documentation for the Presence stanza
                        to see how else it may be used.
        """
        #print("muc_online presence={}".format(presence))

        # According to XMPP protocol
        # https://xmpp.org/extensions/xep-0045.html#createroom-instant
        # when room created, it is locked by default
        # below iq unlock the room to allow other clients join
        time.sleep(2)
        if self.owner:
            retryR = 2
            sucUnlock = False
            while retryR > 0 and not sucUnlock:
                sucUnlock = self.unlock_room()
                if not sucUnlock:
                    print("Not successfully unlock the room, retry: {} remaining".format(retryR))
                    retryR -= 1
                    time.sleep(3)
            if not sucUnlock:
                print("Unlock room failed")

        global g_ready
        g_ready += 1

        if presence['muc']['nick'] != self.nick:
            self.send_message(mto=presence['from'].bare,
                              mbody="Hello, %s %s" % (presence['muc']['role'],
                                                      presence['muc']['nick']),
                              mtype='groupchat')

def start_client(jid, pwd, conf, nick, owner=False):
    xmpp = MUCBot(jid, pwd, conf, nick, owner)
    xmpp.register_plugin('xep_0030') # Service Discovery
    xmpp.register_plugin('xep_0045') # Multi-User Chat
    xmpp.register_plugin('xep_0199') # XMPP Ping

    thrd = XMPPThread(xmpp)
    thrd.start()
    return xmpp

def test_occupant(room, i):
    global g_result
    global g_ready
    global xmpp_domain
    xmpps = []
    N = 10
    if not room:
        room = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(N)) # randomly create
        room += '_{}'.format(i)
    xc = start_client("xx@{}".format(xmpp_domain), '', "{}@conference.{}".format(room, xmpp_domain), 'aaa', True)
    xmpps.append(xc)

    while g_ready < 1:
        time.sleep(1)

    xc = start_client("xx@{}".format(xmpp_domain), '', "{}@conference.{}".format(room, xmpp_domain), 'bbb')
    xmpps.append(xc)

    while g_ready < len(xmpps):
        time.sleep(1)

    g_result[1] = g_result[1] + 1
    if check_clusters(room):
        g_result[0] = g_result[0] + 1

    #time.sleep(300)
    for xmpp in xmpps:
        xmpp.disconnect()
    g_ready = 0

def main():
    # Setup the command line arguments.
    optp = argparse.ArgumentParser()

    # Output verbosity options.
    optp.add_argument('-q', '--quiet', help='set logging to ERROR',
                    action='store_const', dest='loglevel',
                    const=logging.ERROR, default=logging.INFO)
    optp.add_argument('-d', '--debug', help='set logging to DEBUG',
                    action='store_const', dest='loglevel',
                    const=logging.DEBUG, default=logging.INFO)
    optp.add_argument('-v', '--verbose', help='set logging to COMM',
                    action='store_const', dest='loglevel',
                    const=5, default=logging.INFO)

    # XMPP domain and room options.
    optp.add_argument("-m", "--domain", dest="domain",
                    help="XMPP domain")
    optp.add_argument("-r", "--room", dest="room",
                    help="MUC room to join")
    optp.add_argument("-n", "--nodes", dest="nodes", action="append", default=[],
                    help="Openfire Nodes")
    optp.add_argument("-k", "--key", dest="key",
                    help="Openfire shared key")
    optp.add_argument("-l", "--loop", dest="loop", type=int,
                    help="Loops of execution")

    opts = optp.parse_args()

    # Setup logging.
    logging.basicConfig(level=opts.loglevel,
                        format='%(levelname)-8s %(message)s')

    global xmpp_domain
    global room_name
    global openfire_nodes
    global openfire_shared_key

    if opts.domain is not None:
        xmpp_domain = opts.domain
    if opts.room is not None:
        room_name = opts.room
    if opts.nodes is not None and len(opts.nodes) > 0:
        openfire_nodes = opts.nodes
    if opts.key is not None:
        openfire_shared_key = opts.key
    loop = 10
    if opts.loop is not None:
        loop = opts.loop
    for i in range(loop):
        test_occupant(room_name, i)
        print("{} Testing succeed: {}/{}".format(datetime.datetime.now(), g_result[0], g_result[1]))

if __name__ == '__main__':
    main()
    # Using nohup command to execute on background without terminal connection
    # nohup python3 -u muc_cluster_test.py -l 1000 > output.res 2 > output.err
        
