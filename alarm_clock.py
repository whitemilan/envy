#! /usr/bin/env python3

import os
import sys
import time
import threading
import json

class alarm_clock:
    def __init__(self):
        self.ival_sync = 60
        self.file_sync = 'saved_alarms.json'
        self.alarm_times = []
        self.sema_times = threading.Semaphore()
        self.broadcast_function = lambda: print('Placeholder broadcasting \
                function called.')
        self.sema_actions = threading.Semaphore()
        self.management = threading.Thread(target = self.manage)
        self.sema_end = threading.Semaphore()
        self.cond_end = threading.Condition()
        self.bool_end = False
        self.management.start()
        return

    def manage(self):
        print('\nStatus: Start management.\n')
        while threading.main_thread().is_alive() and not self.bool_end:
            self.sema_end.release()
            print('\nStatus: Next management round.\n')
            self.sync_times()
            print('\nTimes: {0}\n'.format(self.active_alarms()))
            self.sema_times.acquire()
            while self.alarm_times and self.alarm_times[-1] < time.time() + self.ival_sync:
                self.thread_check = threading.Thread(target =
                        self.alarm_countdown, args=(self.alarm_times[-1],))
                self.thread_check.start()
                self.alarm_times.pop()
                with open(self.file_sync, 'w') as sync_file:
                    json.dump(self.alarm_times, sync_file)
            self.sema_times.release()
            with self.cond_end:
                self.cond_end.wait(self.ival_sync/2)
            self.sema_end.acquire()
        return

    def add_time(self, minute, hour=-1, weekday=-1):
        print('\nStatus: Add Time.\n')
        now = time.localtime()
        if hour != -1:
            if weekday != -1:
                offset_weekdays = weekday - now[6]
                if offset_weekdays < 0:
                    offset_weekdays = 7 + offset_weekdays
            else: 
                offset_weekdays = 0
            time_alarm = time.mktime(time.strptime(repr(hour) + ' ' + repr(minute)
                         + ' ' + repr(now[0]) + ' ' + repr(now[7] + 
                         offset_weekdays), '%H %M %Y %j'))

            if time_alarm < time.mktime(now):
                time_alarm = time_alarm + 86400
        else:
            time_alarm = time.time() + minute*60
        self.sema_times.acquire()
        self.alarm_times.append(time_alarm)
        self.alarm_times = sorted(list(set(self.alarm_times)), reverse=True)
        self.sema_times.release()
        self.sync_times()
        return

    def sync_times(self):
        print('\nStatus: Synchronyzing Times:\n')
        try:
            with open(self.file_sync, 'r') as sync_file:
                buf_alarm_times = json.load(sync_file)
        except:
            buf_alarm_times = []
        print('Times out of json' + repr(buf_alarm_times))
        
        if buf_alarm_times != self.alarm_times:
            self.sema_times.acquire()
            with open(self.file_sync, 'w') as sync_file:
                self.alarm_times.extend(buf_alarm_times)
                now = time.time()
                self.alarm_times = sorted([i for i in set(self.alarm_times)
                        if now < i], reverse=True)
                json.dump(self.alarm_times, sync_file)
            print('New time list: ' + repr(self.alarm_times))
            self.sema_times.release()
        self.broadcast_function()
        return

    def alarm_countdown(self, time_act):
        print('\nStatus: Alarm countdown starts.\n')
        time_countdown = time_act - time.time()
        if 0 < time_countdown:
            if 60 < time_countdown:
                print('\nStatus: Alarm more than one minute in the future.\n')
                self.sema_times.acquire()
                self.alarm_times.append(time_act)
                self.sema_times.release()
                return
            time.sleep(time_act - time.time())
        elif time_countdown < -60:
            print('\nError: Alarm time lies in past.\n')
            return
        self.start_alarm()
        print('Status: Alarm countdown ends.')
        return
    
    def start_alarm(self):
        print('Alarm')
        self.sema_actions.acquire()
        self.actions()
        self.sema_actions.release()
        return

    def actions(self):
        print('default alarm')
        return
    
    def active_alarms(self):
        with self.sema_times:
            active_times = self.alarm_times
        return [time.strftime('%H:%M, %A %d.%m.', time.localtime(i)) for i in
                active_times[::-1]]

    def set_alarm_action(self, actions):
        self.sema_actions.acquire()
        self.actions = [i.split() for i in actions]
        self.sema_actions.release()
        return

    def delete_alarm(self, no_alarm=-1):
        print('Deleting alarm starts.')
        time_deleted = 0
        self.sync_times()
        with self.sema_times:
            if no_alarm < len(self.alarm_times):
                no_alarm = (no_alarm + 1) * (-1)
                time_deleted = self.alarm_times.pop(no_alarm)
            else: 
                print('Wrong alarm number.')
        with open(self.file_sync, 'w') as sync_file:
            json.dump(self.alarm_times, sync_file)
        self.broadcast_function()
        return
   
    def broadcast_change(self):
        print('Alarm: Broadcast Change: Start.')
        return

    def end(self):
        with self.sema_end:
            self.bool_end = True
        with self.cond_end:
            self.cond_end.notify_all()
        print("Alarm Clock ended sucessfully.")
        return


if __name__ == "__main__":
    print('Start clock')
    clock1 = alarm_clock()
    print('Add times')
    clock1.add_time(30, 13)
    clock1.add_time(31, 13)
    clock1.add_time(32, 13)
    print('3 times added, start waiting loop')
    while True:
        buffer = input('Input time or exit: ')
        if buffer == 'exit':
            print('exiting now')
            clock1.end()
            break
        else:
            try:
                print('Adding time')
                clock1.add_time(buffer)
            except:
                print('Wrong input, try again')
