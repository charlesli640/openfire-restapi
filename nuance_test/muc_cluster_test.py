#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    SleekXMPP: The Sleek XMPP Library
    Copyright (C) 2010  Nathanael C. Fritz
    This file is part of SleekXMPP.

    See the file LICENSE for copying permission.
"""

import sys, time
import logging
import getpass
import threading
from optparse import OptionParser
import sleekxmpp
from sleekxmpp.xmlstream import ElementBase
from xml.etree import cElementTree as ET

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

class XMPPThread(threading.Thread):
    def __init__(self, xmpp):
        threading.Thread.__init__(self)
        self.xmpp = xmpp

    def run(self):
        # Connect to the XMPP server and start processing XMPP stanzas.
        if self.xmpp.connect():
            self.xmpp.process(block=True)
            print("Done")
        else:
            print("Unable to connect.")

class TestThread(threading.Thread):
    def __init__(self,xmpp):
        threading.Thread.__init__(self)
        self.xmpp = xmpp

    def run(self):
        global g_result
        muc1 = Muc("http://charles-openfire-1.magnet.com:9090", "Lz4vLf3yE7FrPWGm")
        rooms1 = muc1.get_rooms()
        print(rooms1)
        muc2 = Muc("http://charles-openfire-2.magnet.com:9090", "Lz4vLf3yE7FrPWGm")
        rooms2 = muc2.get_rooms()
        print(rooms2)
        print("equal={}".format(rooms1 == rooms2))
        g_result[1] = g_result[1] + 1
        if rooms1 == rooms2:
            g_result[0] = g_result[0] + 1
        time.sleep(2)
        self.xmpp.disconnect()


class MUCBot(sleekxmpp.ClientXMPP):

    """
    A simple SleekXMPP bot that will greets those
    who enter the room, and acknowledge any messages
    that mentions the bot's nickname.
    """

    def __init__(self, jid, password, room, nick):
        sleekxmpp.ClientXMPP.__init__(self, jid, password)

        self.room = room
        self.nick = nick

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
        if msg['mucnick'] != self.nick and self.nick in msg['body']:
            self.send_message(mto=msg['from'].bare,
                              mbody="I heard that, %s." % msg['mucnick'],
                              mtype='groupchat')

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
        query = ET.Element('{http://jabber.org/protocol/muc#owner}query')
        x = ET.Element('{jabber:x:data}x', type='submit')
        query.append(x)
        iq = self.make_iq_set(sub=query, ito=self.room)
        iq.send(timeout=60)
        time.sleep(5)
        print("Ready")
        # trigger testing thread
        testT = TestThread(self)
        testT.start()

        if presence['muc']['nick'] != self.nick:
            self.send_message(mto=presence['from'].bare,
                              mbody="Hello, %s %s" % (presence['muc']['role'],
                                                      presence['muc']['nick']),
                              mtype='groupchat')

def test_occupant():
    xmpp = MUCBot('focus@jitsi-meet-charles.magnet.com', '0D06eLS1', '12345@conference.jitsi-meet-charles.magnet.com', 'focus')
    xmpp.register_plugin('xep_0030') # Service Discovery
    xmpp.register_plugin('xep_0045') # Multi-User Chat
    xmpp.register_plugin('xep_0199') # XMPP Ping

    if xmpp.connect():
        xmpp.process(block=True)
        #print("Done")
    else:
        print("Unable to connect.")
    #thrd = XMPPThread(xmpp)
    #thrd.start()


if __name__ == '__main__':
    # Setup the command line arguments.
    optp = OptionParser()

    # Output verbosity options.
    optp.add_option('-q', '--quiet', help='set logging to ERROR',
                    action='store_const', dest='loglevel',
                    const=logging.ERROR, default=logging.INFO)
    optp.add_option('-d', '--debug', help='set logging to DEBUG',
                    action='store_const', dest='loglevel',
                    const=logging.DEBUG, default=logging.INFO)
    optp.add_option('-v', '--verbose', help='set logging to COMM',
                    action='store_const', dest='loglevel',
                    const=5, default=logging.INFO)

    # JID and password options.
    optp.add_option("-j", "--jid", dest="jid",
                    help="JID to use")
    optp.add_option("-p", "--password", dest="password",
                    help="password to use")
    optp.add_option("-r", "--room", dest="room",
                    help="MUC room to join")
    optp.add_option("-n", "--nick", dest="nick",
                    help="MUC nickname")

    opts, args = optp.parse_args()

    # Setup logging.
    logging.basicConfig(level=opts.loglevel,
                        format='%(levelname)-8s %(message)s')

    '''
    if opts.jid is None:
        opts.jid = raw_input("Username: ")
    if opts.password is None:
        opts.password = getpass.getpass("Password: ")
    if opts.room is None:
        opts.room = raw_input("MUC room: ")
    if opts.nick is None:
        opts.nick = raw_input("MUC nickname: ")
    '''
    for i in range(20):
        test_occupant()
        print("Testing succeed: {}/{}".format(g_result[0], g_result[1]))
    