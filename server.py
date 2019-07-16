#! /usr/bin/env python3

###############################################################################
#
# MIT License (MIT)
#
# Copyright (c) Tavendo GmbH
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
###############################################################################

from autobahn.twisted.websocket import WebSocketServerProtocol, WebSocketServerFactory
import json
import subprocess
import os
import threading
import queue
import time
import alarm_clock
import local_differences
import mpd_jan

local_diff = local_differences.differences()

def lircstop():
    output_bash = subprocess.Popen(('irsend', 'SEND_START', 'Teufel-IP42RC', 'KEY_POWER'), stdout=subprocess.PIPE)
    time.sleep(.5)
    output_bash = subprocess.Popen(('irsend', 'SEND_STOP', 'Teufel-IP42RC', 'KEY_POWER'), stdout=subprocess.PIPE)
    return

class MyServerProtocol(WebSocketServerProtocol):
    
    def onConnect(self, request):
        print("Client connecting: {0}".format(request.peer))

    def onOpen(self):
        print("WebSocket connection open.")
        self.factory.register(self)
        message = {'alarms':self.factory.alarm.active_alarms(),
                   'playlists': self.factory.client_mpd.playlists, 
                   'songlist': self.factory.client_mpd.playlist, 
                   'status' : self.factory.client_mpd.status, 
                   'ls' : self.factory.client_mpd.ls()}
        json_message = json.dumps(message)
        self.sendMessage(json_message.encode('utf8'))

        
    def onMessage(self, payload, isBinary):
        # echo back message verbatim
        msg = json.loads(payload.decode('utf8'))
        msg['client'] = self
        #print("Type is: {0}".format(ab_msg['msg_type']))
        self.factory.queue_messages.put(msg)

    def onClose(self, wasClean, code, reason):
        self.factory.unregister(self)
        print("WebSocket connection closed: {0}".format(reason))
    


class BroadcastServerFactory(WebSocketServerFactory):

    """
    Simple broadcast server broadcasting any message it receives to all
    currently connected clients.
    """

    def __init__(self, url, client_mpd, alarm, debug=False, debugCodePaths=False):
        WebSocketServerFactory.__init__(self, url)
        self.clients = []
        self.tickcount = 0
        self.client_mpd = client_mpd
        self.alarm = alarm

        self.queue_broadcast = queue.Queue()
        thread_broadcast = threading.Thread(target=self.broadcast)
        thread_broadcast.start()

        self.queue_sc_message = queue.Queue()
        thread_sc_message = threading.Thread(target=self.sent_to_single_client)
        thread_sc_message.start()
        
        self.queue_messages = queue.Queue()
        thread_process_tasks = threading.Thread(target=self.process_tasks)
        thread_process_tasks.start()
        
        alarm.broadcast_function = lambda: self.queue_broadcast.put({'alarms':
            self.alarm.active_alarms()})
        self.client_mpd.broadcast_playlist = \
            lambda: self.queue_broadcast.put({'songlist': self.client_mpd.playlist})
        self.client_mpd.broadcast_playlists = \
            lambda: self.queue_broadcast.put({'playlists': self.client_mpd.playlists})
        self.client_mpd.broadcast_status = \
            lambda: self.queue_broadcast.put({'status': self.client_mpd.status})
        
    def register(self, client):
        if client not in self.clients:
            # if not self.clients:
            #     self.client_mpd.connect()
            print("Register client {}".format(client.peer))
            self.clients.append(client)

    def unregister(self, client):
        if client in self.clients:
            print("Unregister client {}".format(client.peer))
            self.clients.remove(client)
        # if not self.clients:
        #     self.client_mpd.disconnect()

    def sent_to_single_client(self):
        while threading.main_thread().is_alive():
            sc_message = self.queue_sc_message.get()
            print("Sending message to single client now")
            if sc_message is None:
                break
            else:
                sc_message[0].sendMessage(json.dumps(sc_message[1]).encode('utf8'))

    def broadcast(self):
        while threading.main_thread().is_alive():
            bc_message = self.queue_broadcast.get()
            if bc_message is None:
                print("Broadcasting exited successfully.")
                break
            if self.getConnectionCount():
                if bc_message is 'all':
                    bc_message = {'alarms':self.alarm.active_alarms(),
                        'playlists': self.client_mpd._playlists, 
                        'songlist': self.client_mpd._playlist}
                json_stream = json.dumps(bc_message)
                #reactor.callLater(1, self.tick)
                print('Broadcast Message: {0}'.format(json_stream))
                # preparedMsg = self.prepareMessage(msg.encode('utf8'))
                for i in self.clients:
                    i.sendMessage(json_stream.encode('utf8'))
                # sendPreparedMessage(self.clients[0], preparedMsg)
    
    def process_tasks(self):
        tasklist = {
            'power': lambda message: lircstop(),
            'toggle': lambda message: self.client_mpd.toggle(), 
            'stop': lambda message: self.client_mpd.stop(), 
            'prev': lambda message: self.client_mpd.previous(),
            'next': lambda message: self.client_mpd.next(),
            'jump_to': lambda message: self.client_mpd.play(message['song']),
            'move_songs': lambda message: \
                self.client_mpd.move(message['song'], \
                message['destination']),
            'source_up': lambda message:subprocess.Popen(('irsend', 'SEND_ONCE', 'Teufel-IP42RC', 'KEY_UP'), stdout=subprocess.PIPE),
            'source_down': lambda message:subprocess.Popen(('irsend', 'SEND_ONCE', 'Teufel-IP42RC', 'KEY_DOWN'), stdout=subprocess.PIPE),
            'vol_down': lambda message:subprocess.Popen(('irsend', 'SEND_ONCE', 'Teufel-IP42RC', 'KEY_VOLUMEDOWN'), stdout=subprocess.PIPE),
            'vol_up': lambda message:subprocess.Popen(('irsend', 'SEND_ONCE', 'Teufel-IP42RC', 'KEY_VOLUMEUP'), stdout=subprocess.PIPE),
            'shuffle': lambda message: self.client_mpd.shuffle(),
            'clear': lambda message: self.client_mpd.clear(),
            'update': lambda message: self.client_mpd.update(),
            'load_playlist': lambda message: self.client_mpd.load(message['playlist']),
            'delete_playlist': lambda message: self.client_mpd.rm(message['playlist']),
            'save_playlist': lambda message: self.client_mpd.save(message["playlistname"]),
            'add_file': lambda message: self.client_mpd.add(message['file']),
            'delete_songs': lambda message: 
                self.client_mpd.delete(message['selected_songs']),
            'speaker_power': lambda message: subprocess.Popen(('sudo',
                '/srv/http/gpio_switch.py', '17', 'toggle'),
                stdout=subprocess.PIPE),
            'add_alarm': lambda message: self.alarm.add_time(int(message['minutes']),
                int(message['hours'])), 
            'delete_alarm': lambda message:
            self.alarm.delete_alarm(int(message['no_alarm'])),
            'ask_for_status': lambda message: self.client_mpd.player(),
            'open_folder': lambda message: self.queue_sc_message.put([message['client'], {'ls': self.client_mpd.ls(message['folder'])}]) 
                # self.client_mpd.library[message['ls']]])
            # 'open_folder':lambda message: print(self.client_mpd.library['Die Ärzte']),
            }
        while threading.main_thread().is_alive():
            message = self.queue_messages.get()
            if message is None:
                print("Process_tasks exited successfully")
                break
            #try:
            print(message)
            tasklist[message['task']](message)
            #except:
            #    print('Error in tasklist occured.')
            self.queue_messages.task_done()

class alarm_clock(alarm_clock.alarm_clock):
    def actions(self):
        print('Alarm starts. yeah')
        try:
            lircstop()
        except:
            print('IRSEND did not work')

        client_mpd.clear()
        print("Not clear")
        client_mpd.load('wakeup')
        print("Not wakeup")
        client_mpd.shuffle()
        client_mpd.play()
        print("Not not shuffle")
        client_mpd.play()
        print("Not play")



if __name__ == '__main__':

    import sys
    import subprocess
    import os
    import signal

    from twisted.python import log
    from twisted.internet import reactor
    client_mpd = mpd_jan.mpd_jan('localhost', 6600)
    client_mpd.connect()
    log.startLogging(sys.stdout)
    def cleanup(signal, frame):
        print('Exiting after cleanup.')
        reactor.sigInt()
        client_mpd.disconnect()
        factory.queue_messages.put(None)
        factory.queue_broadcast.put(None)
        factory.queue_sc_message.put(None)
        alarm.end()
    
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)
    
    alarm = alarm_clock()

    factory = BroadcastServerFactory("ws://127.0.0.1:9000", client_mpd,
            alarm, debug=False)
    factory.protocol = MyServerProtocol
    # factory.setProtocolOptions(maxConnections=2)
    reactor.listenTCP(9000, factory)
    reactor.run()
