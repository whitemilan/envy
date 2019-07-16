#! /usr/bin/env python3

from mpd import MPDClient, ConnectionError
from mpd.base import CommandError
import threading
import queue
import time
import select



class mpd_jan:
    def __init__(self, host, port):
        self._host = host
        self._port = port
        self._watcher = MPDClient()
        self._sender = MPDClient()
        self._sender.watcher_player = self.player
        self._sender.watcher_options = self.player
        self._sender.watcher_playlist = self.get_playlist
        self._sender.watcher_stored_playlist = self.stored_playlist
        self._sender.watcher_update = self.watcher_update
        self._sender.watcher_database = self.watcher_database
        self._sender.watcher_sticker = self.watcher_sticker
        self._sender.watcher_mixer = self.watcher_mixer
        self.exit_sender, self.exit_watcher = False, False
        self.queue_sender = queue.Queue()
        self.queue_watcher = queue.Queue()
        self.queue_output = queue.Queue()
        self._playlist = []
        self.sema_playlist = threading.Semaphore()
        self._status = {}
        self.sema_status = threading.Semaphore()
        self._playlists = []
        self.sema_playlists = threading.Semaphore()
        self._library = []
        self.sema_library = threading.Semaphore()

    def cycle_watcher(self):
        self._watcher.connect(self._host, self._port)
        while threading.main_thread().is_alive() and not self.exit_watcher:
            print('Watcher cycle round starts.')
            try:
                for i in self._watcher.idle():
                    print("Watched message: "+i)
                    self.queue_sender.put_nowait(['watcher_'+i,
                    [], {}])
            except:
                print('Watcher round experienced an error. Restart cycle.')
            print('Watcher cycle round ends.')
        try:
            self._watcher.disconnect()
        except:
            print('Watcher wouldn\'t close, attempting to kill watcher.')
            # self._watcher.kill()
        print('Watcher disconnected.')
    
    def cycle_sender(self):
        while threading.main_thread().is_alive() and not self.exit_sender:
            print('Sender cycle round starts.')
            function, args, kwargs = self.queue_sender.get()
            print(function)
            for i in range(2):
                try:
                    print('Command is being send to mpd')
                    out = getattr(self._sender, function)(*args, **kwargs)
                    # print('Got from sending: ')
                    # print(out)
                    if function == 'lsinfo': 
                        self.queue_output.put(out)
                    break
                except ConnectionError as e:
                    print('Error during sender cycle: {0}'.format(e))
                    print('Reconnecting...')
                    self._sender.connect(self._host, self._port)
                    print('Reconnection sucessful.')
                except BrokenPipeError as e:
                    print('Error during sender cycle: {0}'.format(e))
                    print('Setting up a new sender...')
                    self._sender = MPDClient()
                    self._sender.watcher_player = self.player
                    self._sender.watcher_options = self.player
                    self._sender.watcher_playlist = self.get_playlist
                    self._sender.watcher_stored_playlist = self.stored_playlist
                    self._sender.watcher_update = self.watcher_update
                    self._sender.watcher_database = self.watcher_database
                    self._sender.watcher_sticker = self.watcher_sticker
                    self._sender.watcher_mixer = self.watcher_mixer
                    self._sender.connect(self._host, self._port)
                    print('New sender set up.')
                except CommandError as e:
                    print('Command Error: {0}'.format(e))
            self.queue_sender.task_done()
            print('Sender cycle round ends.')
        try:
            self._sender.disconnect()
        except:
            print('Sender wouldn\'t close, attempting to kill sender.')
            # self._sender.kill()
        print('Sender disconnected.')

    play = lambda self, number_song=-1: self.queue_sender.put(['play',
        [number_song], {}])
    pause = lambda self: self.queue_sender.put(['pause', [], {}])
    stop = lambda self: self.queue_sender.put(['stop', [], {}])
    next = lambda self: self.queue_sender.put(['next', [], {}])
    previous = lambda self: self.queue_sender.put(['previous', [], {}])
    shuffle = lambda self: self.queue_sender.put(['shuffle', [], {}])
    clear = lambda self: self.queue_sender.put(['clear', [], {}])
    random = lambda self, state: self.queue_sender.put(['random', [state], {}])
    load = lambda self, name_playlist: self.queue_sender.put(['load',
        [name_playlist], {}])
    rm = lambda self, name_playlist: self.queue_sender.put(['rm', [name_playlist], {}])
    add = lambda self, filename: self.queue_sender.put(['add', [filename], {}])
    move = lambda self, songs, destination: self.queue_sender.put(['move',
        [songs, destination], {}])
    update = lambda self: self.queue_sender.put(['update', [], {}])
    save = lambda self, playlistname: self.queue_sender.put(['save', [playlistname], {}])

    def delete(self, selected_songs):
        print('Deleting songs')
        print(selected_songs)
        for i in selected_songs:
            self.queue_sender.put(['delete', [i], {}])
    
    # = lambda self: self.queue_sender.put(['', [], {}])
    def toggle(self):
        if self.status['state'] != 'play':
            self.play()
        else:
            self.pause()
    
    def player(self):
        self.status = self._sender.status()
        self.broadcast_status() 
    
    def get_playlist(self):
        self.playlist = ['{0} - {1}'.format(i['artist'], i['title']) if 'artist' in i and 'title' in i else
                 str(i['file']) for i in self._sender.playlistinfo()]
        print("broadcasting playlist")
        self.broadcast_playlist()
        print("Broadcasting status")
        self.broadcast_status()

    def stored_playlist(self):
        self.playlists = [i['playlist'] for i in self._sender.listplaylists()]
        self.broadcast_playlists()

    def watcher_update(self):    
        full_info = self._sender.listall()
        path_and_title_files = {i.get('directory'):[[],[]] for i in full_info if i.get('directory')}
        path_and_title_files['/'] = [[],[]]
        for i in full_info:
            entry = i.get('directory')
            if entry:
                path, sep, filename = entry.rpartition('/')
                if path:
                    path_and_title_files[path][0].append(filename)
                else:
                    path_and_title_files['/'][0].append(filename)
            entry = i.get('file')
            if entry:
                path, sep, filename = entry.rpartition('/')
                if path:            
                    path_and_title_files[path][1].append(filename)
                else:
                    path_and_title_files['/'][1].append(filename)
        self.library = path_and_title_files
        # self.broadcast_library()
    
    def watcher_database(self):
        pass
    
    def watcher_sticker(self):
        pass
    
    def watcher_mixer(self):
        pass
    
    def ls(self, folder=''):
        self.queue_sender.put(['lsinfo', [folder], {}])
        files = []
        directories = []
        for i in self.queue_output.get():
            if 'directory' in i:
                directories.append(i['directory'])
            elif 'file' in i:
                files.append(i['file'])
        return [directories, files]

    def broadcast_status(self):
        print('Broadcasting status:')
        print(self.status)        
        print('Broadcasting ends.')
    
    def broadcast_playlist(self):
        print('Broadcasting playlist:')
        print(self.playlist)
        print('Broadcasting playlist.')
    
    def broadcast_playlists(self):
        print('Broadcasting playlist:')
        print(self.playlists)
        print('Broadcasting playlist.')

    def broadcast_library(self):
        print('Broadcasting library:')
        print(self.library)
        print('Broadcasting library.')

    def disconnect(self):
        print('Attempting to disconnect.')
        state_random = bool(int(self.status['random']))
        self.exit_watcher = True
        print("sending random")
        self.random(int(not state_random))
        time.sleep(1)
        self.exit_sender = True
        self.random(int(state_random))
        print('Disconnection successful.')

    def connect(self):
        print('Reconnecting...')
        self.exit_watcher = False
        self.exit_sender = False
        self._sender.connect(self._host, self._port)
        self.status = self._sender.status()
        self.playlist = ['{0} - {1}'.format(i['artist'], i['title']) if 'artist' in i 
                and 'title' in i else str(i['file']) for i in 
                self._sender.playlistinfo()]
        self.playlists = [i['playlist'] for i in self._sender.listplaylists()]
        self.watcher_update()
        thread_watcher = threading.Thread(target=self.cycle_watcher)
        thread_watcher.start()
        thread_sender = threading.Thread(target=self.cycle_sender)
        thread_sender.start()
        print('Reconnected.')

    @property
    def playlist(self):
        with self.sema_playlist:
            buf = self._playlist
        return buf

    @playlist.setter
    def playlist(self, value):
        with self.sema_playlist:
            self._playlist = value
        return

    @property
    def status(self):
        with self.sema_status:
            buf = self._status.copy()
        return buf

    @status.setter
    def status(self, value):
        with self.sema_status:
            self._status = value
        return

    @property
    def playlists(self):
        with self.sema_playlists:
            buf = self._playlists.copy()
        return buf

    @playlists.setter
    def playlists(self, value):
        with self.sema_playlists:
            self._playlists = value
        return
    
    @property
    def library(self):
        with self.sema_library:
            buf = self._library.copy()
        return buf

    @library.setter
    def library(self, value):
        with self.sema_library:
            self._library = value
        return


if __name__ == "__main__":
    client = mpd_jan('localhost', 6600)
    client.connect()
    
    print(client.ls('David Guetta'))
    print('Thats it')
    time.sleep(5)

    client.disconnect()
