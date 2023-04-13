#! /usr/bin/env python3
import traceback
import sys
import random
from math import sqrt, pow
from datetime import datetime
import numpy as np
from sklearn.decomposition import PCA
from scipy import signal
from scipy.signal import find_peaks
import subprocess
from statistics import mean
import websocket
import json
import threading
import urllib.request
import gtts
import pygame
import time

running = True

def cre8msg(msg, fname):
    tts = gtts.gTTS(msg, lang = 'ru')
    tts.save(f'audio/{fname}.mp3')

def saymsg(fname, vol=0.25):
    pygame.mixer.music.load(f'audio/{fname}.mp3')
    pygame.mixer.music.set_volume(vol)
    pygame.mixer.music.play()

def timed_log(s):
    print(f'{datetime.now()}: {s}')

class TMyApplication:
    def __init__(self):
        #self.address = "192.168.1.185:8080"
        self.address = "192.168.4.32:8080"
        #self.address = "127.0.0.1:8080"
        self.debug = False

        self.interval_dir_cnt = 5
        self.interval_dir_num = 0
        if self.debug:
            self.interval_dir_period = 10
            self.interval_ndir_period = 15
        else:
            self.interval_dir_period = 3*60
            self.interval_ndir_period = 40*60

        self.alarm_period = 5
        self.sample_rate = 25

        self.val = []
        self.x_data = []
        self.y_data = []
        self.z_data = []
        self.xc_data = []
        self.yc_data = []
        self.zc_data = []
        self.pc_data = []
        self.peaks = []
        self.time_data = []
        self.alarm_time = 0

        self.sound_volume_pc = 1

        self.interval_timer = None
        self.alarm_timer = None

    def timer_start(self):
        self.interval_timer = LoopTimer(self.interval_dir_period, self.interval)
        self.interval_timer.start()

    def timer_stop(self):
        if self.interval_timer is not None:
          self.interval_timer.cancel()
          self.interval_timer = None

        if self.alarm_timer is not None:
          self.alarm_timer.cancel()
          self.alarm_timer = None

    def run(self):
        global running

        sys.stdout.write('Подготавливаем голосовые сообщения...')
        cre8msg('Привет...', 'hi')
        cre8msg('Это же сон!', 'alarm-0')
        cre8msg('Ты во сне!', 'alarm-1')
        cre8msg('Ты знаешь, что ты во сне?', 'alarm-2')
        cre8msg('Осознавайся!', 'alarm-3')
        cre8msg('Принято!', 'off')
        cre8msg('Начинаем прямой метод.', 'dir-mtd')
        cre8msg('Начинаем непрямой метод.', 'ndir-mtd')
        cre8msg('Ошибка подключения к акселерометру.', 'sens-srv-err')
        sys.stdout.write('Ok!\n')

        random.seed(datetime.now().timestamp())

        pygame.init()
        pygame.mixer.init()

        saymsg('hi')
        time.sleep(1)

        while(True):
          running = True
          # Подключаемся к Sensor Server для доступа к данным акселерометра смартфона:
          sensor = Sensor(self, self.address, "android.sensor.accelerometer")
          sensor.connect() # asynchronous call

          try:
            while running:
              pass

            if sensor.is_error:
              saymsg('sens-srv-err')
              time.sleep(3)
              continue

          except KeyboardInterrupt:
            print('Выходим...')

          sensor.disconnect()
          break

        pygame.quit()
        res = 0

        return res

    def on_alarm_cancel(self):
        saymsg('off', self.sound_volume_pc / 100.0)

        self.sound_volume_pc = 1
        self.alarm_time = 0

    def interval(self):
        if self.alarm_timer is None:
            if self.interval_dir_cnt:
                if self.interval_dir_num < self.interval_dir_cnt:
                    self.interval_dir_num += 1
                else:
                    self.interval_timer.cancel()
                    self.interval_dir_cnt = 0
                    timed_log('Начинаем непрямой метод.')
                    saymsg('ndir-mtd', self.sound_volume_pc / 100.0)
                    self.interval_timer = LoopTimer(self.interval_ndir_period, self.interval)
                    self.interval_timer.start()
                    return

            self.alarm_timer = LoopTimer(self.alarm_period, self.alarm, self.on_alarm_cancel)
            self.alarm_timer.start()

    def alarm(self):
        timed_log('сработал будильник')
        saymsg(f'alarm-{random.randint(0, 3)}', self.sound_volume_pc / 100.0)

        if self.sound_volume_pc < 100:
            self.sound_volume_pc += 2
        else:
            self.sound_volume_pc = 100

        if not self.alarm_time:
            # последний элемент может быть ещё не заполнен:
            self.alarm_time = self.time_data[-2]

def get_last_movavg(a, ws=3):
    sz = len(a)
    wsz = min(sz, ws)
    res = 0
    for i in range(wsz):
        res += a[-(i+1)]

    return res / wsz

def add_movavg(a, v, ws=5):
    a.append(v)
    a[-1] = get_last_movavg(a)

class Sensor:
    #constructor
    def __init__(self, myapp, address, sensor_type):
        self.address = address
        self.sensor_type = sensor_type
        self.length = 0
        self.is_pca_inc = False
        self.last_peak = -1
        self.sample_rate = myapp.sample_rate
        self.max_window_dur = 10
        self.max_window_size = self.max_window_dur * self.sample_rate
        self.myapp = myapp
        self.is_error = False

    # called each time when sensor data is recieved
    def on_message(self, ws, message):
        values = json.loads(message)['values']
        timestamp = json.loads(message)['timestamp']

        if self.length == self.max_window_size:
            self.myapp.val.pop(0)
            self.myapp.x_data.pop(0)
            self.myapp.y_data.pop(0)
            self.myapp.z_data.pop(0)
            self.myapp.xc_data.pop(0)
            self.myapp.yc_data.pop(0)
            self.myapp.zc_data.pop(0)

            if self.is_pca_inc:
                self.myapp.pc_data.pop(0)

            self.myapp.time_data.pop(0)

        self.myapp.val.append(values)
        self.length = len(self.myapp.val)
        self.myapp.time_data.append(timestamp / 1000000000.0)

        x = values[0]
        y = values[1]
        z = values[2]

        self.myapp.x_data.append(x)
        self.myapp.y_data.append(y)
        self.myapp.z_data.append(z)
        add_movavg(self.myapp.xc_data, x)
        add_movavg(self.myapp.yc_data, y)
        add_movavg(self.myapp.zc_data, z)

        if self.length > 15:
            if not self.is_pca_inc:
                self.myapp.pc_data.clear()

            # Фильтр 2-го порядка для частот выше 2-х Герц.
            sos = signal.butter(2, 2, 'lp', fs=self.sample_rate, output='sos')
            self.myapp.xc_data[-1] = signal.sosfilt(sos, self.myapp.x_data).tolist()[-1]
            self.myapp.xc_data[-1] = get_last_movavg(self.myapp.xc_data)
            self.myapp.yc_data[-1] = signal.sosfilt(sos, self.myapp.y_data).tolist()[-1]
            self.myapp.yc_data[-1] = get_last_movavg(self.myapp.yc_data)
            self.myapp.zc_data[-1] = signal.sosfilt(sos, self.myapp.z_data).tolist()[-1]
            self.myapp.zc_data[-1] = get_last_movavg(self.myapp.zc_data)

            valc = []
            for i in range(self.length):
                valc.append([self.myapp.xc_data[i], self.myapp.yc_data[i], self.myapp.zc_data[i]])

            n_components = 1
            #if self.length >= n_components:
            av = np.array(valc)
            pca = PCA(n_components=n_components)

            r = pca.fit_transform(av)
            if self.is_pca_inc:
                self.myapp.pc_data[-1] = r[-1][0]
            else:
                for i in range(self.length):
                    self.myapp.pc_data.append(r[i][0])

            minPeakHeight = 0.05 #np.std(self.myapp.pc_data)  # this should be tuned
            pks, peak_props = find_peaks(self.myapp.pc_data, height=minPeakHeight, distance=self.sample_rate // 2, prominence=0.1)
            self.myapp.peaks = [0 for i in range(self.length)]
            for i in pks:
                self.myapp.peaks[i] = 1

            if len(pks) >= 2:
                lp = pks[-1]
                pp = pks[-2]

                # Если сработал таймер, и двойной выдох был сделан после срабатывания:
                if (self.myapp.alarm_timer is not None) and (self.myapp.alarm_time) and (self.myapp.time_data[lp] >= self.myapp.alarm_time) and (self.myapp.time_data[pp] >= self.myapp.alarm_time):
                    d = lp - pp
                    d /= self.sample_rate
                    if d <= 1.25:
                        timed_log('принят двойной выдох')
                        self.myapp.alarm_timer.cancel()
                        self.myapp.alarm_timer = None

        else:
            self.myapp.pc_data.append(0)
            self.myapp.peaks.append(0)

    def on_error(self,ws, error):
        print("error occurred")
        print(error)
        self.is_error = True

    def on_close(self, ws, close_code, reason):
        global running
        running = False
        print("connection close")
        print("close code : ", close_code)
        print("reason : ", reason  )
        self.myapp.timer_stop()

    def on_open(self, ws):
        print(f"connected to : {self.address}")

        timed_log('Начинаем прямой метод.')
        saymsg('dir-mtd')
        self.myapp.timer_start()

    # Call this method on seperate Thread
    def make_websocket_connection(self):
        self.ws = websocket.WebSocketApp(f"ws://{self.address}/sensor/connect?type={self.sensor_type}",
                                on_open=self.on_open,
                                on_message=self.on_message,
                                on_error=self.on_error,
                                on_close=self.on_close)

        # blocking call
        self.ws.run_forever()

    # make connection and start recieving data on sperate thread
    def connect(self):
        thread = threading.Thread(target=self.make_websocket_connection)
        thread.start()

    def disconnect(self):
        if self.ws.sock:
          self.ws.sock.close()

class LoopTimer(threading.Thread):
    def __init__(self, interval, function, on_cancel=None, args=None, kwargs=None):
        super().__init__()
        self.interval = interval
        self.function = function
        self.args = args if args is not None else []
        self.kwargs = kwargs if kwargs is not None else {}
        self.finished = threading.Event()
        self.on_cancel = on_cancel

    def cancel(self):
        """Stop the timer if it hasn't finished yet."""
        self.finished.set()

    def run(self):
        while not self.finished.is_set():
            if not self.finished.wait(self.interval):
                self.function(*self.args, **self.kwargs)

        if self.on_cancel:
            self.on_cancel()

myapp = TMyApplication()
res = myapp.run()

sys.exit(res)
