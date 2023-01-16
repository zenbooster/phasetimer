#! /usr/bin/env python3
"""
Python code to show real time plot from live accelerometer's
data recieved via SensorServer app over websocket 

"""
from math import sqrt, pow
from PyQt5 import QtWidgets, QtCore
import pyqtgraph as pg
import numpy as np
from sklearn.decomposition import PCA
from scipy import signal
from scipy.signal import find_peaks
import subprocess
from statistics import mean
import sys  # We need sys so that we can pass argv to QApplication
import websocket
import json
import threading
import urllib.request

#shared data
#address = "192.168.1.137:8080"
address = "192.168.4.40:8080"
sample_rate = 50
max_window_dur = 10
max_window_size = max_window_dur * sample_rate

val = []
x_data = []
y_data = []
z_data = []
xc_data = []
yc_data = []
zc_data = []
pc_data = []
peaks = []
time_data = []

x_data_color = "#d32f2f"   # red
y_data_color = "#7cb342"   # green
z_data_color = "#0288d1"   # blue
#da_data_color = "#dada00"   # yellow
#ee_data_color = "#ee00ee"   # magenta
pc_data_color = "#000000"   # black
peaks_color = "#d32f2f"   # red

background_color = "#fafafa" # white (material)

lock_draw = threading.Lock();


class Sensor:
    #constructor
    def __init__(self,address,sensor_type):
        self.address = address
        self.sensor_type = sensor_type
        self.length = 0
        self.is_pca_inc = False
        self.last_peak = -1
    
    # called each time when sensor data is recieved
    def on_message(self,ws, message):
        #global xc_data, yc_data, zc_data
        global peaks, alarm_timer
        
        with lock_draw:
            values = json.loads(message)['values']
            timestamp = json.loads(message)['timestamp']

            if self.length == max_window_size:
                val.pop(0)
                x_data.pop(0)
                y_data.pop(0)
                z_data.pop(0)
                xc_data.pop(0)
                yc_data.pop(0)
                zc_data.pop(0)

                if self.is_pca_inc:
                    pc_data.pop(0)
                    #peaks.pop(0)

                time_data.pop(0)
                
            val.append(values)
            self.length = len(val)
            time_data.append(float(timestamp/1000000))

            x = values[0]
            y = values[1]
            z = values[2]

            x_data.append(x)
            y_data.append(y)
            z_data.append(z)
            xc_data.append(x)
            yc_data.append(y)
            zc_data.append(z)

            if self.length > 15:
                if not self.is_pca_inc:
                    pc_data.clear()
                    #peaks.clear()

                #print('HIT.1')
                
                #x_data[-1] = x
                #y_data[-1] = y
                #z_data[-1] = z

                #print('HIT.2')
                # Фильтр 2-го порядка для частот выше 2-х Герц.
                sos = signal.butter(2, 2, 'lp', fs=sample_rate, output='sos')
                xc_data[-1] = signal.sosfilt(sos, x_data).tolist()[-1]
                yc_data[-1] = signal.sosfilt(sos, y_data).tolist()[-1]
                zc_data[-1] = signal.sosfilt(sos, z_data).tolist()[-1]
                #print('HIT.3')

                valc = []
                for i in range(self.length):
                    valc.append([xc_data[i], yc_data[i], zc_data[i]])

                n_components = 1
                #if self.length >= n_components:
                av = np.array(valc)
                pca = PCA(n_components=n_components)

                r = pca.fit_transform(av)
                if self.is_pca_inc:
                    pc_data[-1] = r[-1][0]
                else:
                    for i in range(self.length):
                        pc_data.append(r[i][0])
                
                minPeakHeight = 0.05 #np.std(pc_data)  # this should be tuned
                pks, peak_props = find_peaks(pc_data, height=minPeakHeight, distance=sample_rate // 2)
                #print('HIT.4')
                peaks = [0 for i in range(self.length)]
                #print(f'HIT.5: {len(peaks)}')
                for i in pks:
                    peaks[i] = 1
                
                if len(pks) >= 2:
                    lp = pks[-1]
                    #print(f'self.last_peak={self.last_peak}, lp={lp}')
                    #if self.last_peak != lp:
                    #    self.last_peak = lp
                    if alarm_timer is not None:

                        d = lp - pks[-2]
                        d /= sample_rate
                        if d <= 1:
                            print('!! HIT !!')
                            #if alarm_timer is not None:
                            alarm_timer.cancel()
                            alarm_timer = None

                if self.length == max_window_size and self.last_peak > -1:
                    self.last_peak -= 1

                #print(f'HIT.6: {len(x_data)}, {len(y_data)}, {len(z_data)}, {len(valc)}, {len(pc_data)}, {len(peaks)}, {len(time_data)}')
            else:
                pc_data.append(0)
                peaks.append(0)
                
    def on_error(self,ws, error):
        print("error occurred")
        print(error)

    def on_close(self,ws, close_code, reason):
        app.quit()
        print("connection close")
        print("close code : ", close_code)
        print("reason : ", reason  )

    def on_open(self,ws):
        print(f"connected to : {self.address}")

    # Call this method on seperate Thread
    def make_websocket_connection(self):
        ws = websocket.WebSocketApp(f"ws://{self.address}/sensor/connect?type={self.sensor_type}",
                                on_open=self.on_open,
                                on_message=self.on_message,
                                on_error=self.on_error,
                                on_close=self.on_close)

        # blocking call
        ws.run_forever() 
    
    # make connection and start recieving data on sperate thread
    def connect(self):
        thread = threading.Thread(target=self.make_websocket_connection)
        thread.start()           



class MainWindow(QtWidgets.QMainWindow):

    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        self.graphWidget = pg.PlotWidget()
        self.setCentralWidget(self.graphWidget)

        self.graphWidget.setBackground(background_color)

        self.graphWidget.setTitle("Accelerometer Plot", color="#8d6e63", size="20pt")
        
        # Add Axis Labels
        styles = {"color": "#f00", "font-size": "15px"}
        self.graphWidget.setLabel("left", "m/s^2", **styles)
        self.graphWidget.setLabel("bottom", "Time (miliseconds)", **styles)
        self.graphWidget.addLegend()

        #self.x_data_line =  self.graphWidget.plot([],[], name="x", pen=pg.mkPen(color=x_data_color))
        #self.y_data_line =  self.graphWidget.plot([],[], name="y", pen=pg.mkPen(color=y_data_color))
        #self.z_data_line =  self.graphWidget.plot([],[], name="z", pen=pg.mkPen(color=z_data_color))
        self.pc_data_line =  self.graphWidget.plot([],[], name="pc", pen=pg.mkPen(color=pc_data_color))
        self.peaks_line =  self.graphWidget.plot([],[], name="peaks", pen=pg.mkPen(color=peaks_color))
      
        self.timer = QtCore.QTimer()
        self.timer.setInterval(50)
        self.timer.timeout.connect(self.update_plot_data) # call update_plot_data function every 50 milisec
        self.timer.start()

    def update_plot_data(self):
        with lock_draw:
            # limit lists data to 1000 items 
            limit = -1000 

            # Update the data.
            #self.x_data_line.setData(time_data[limit:], x_data[limit:])  
            #self.y_data_line.setData(time_data[limit:], y_data[limit:])
            #self.z_data_line.setData(time_data[limit:], z_data[limit:])
            self.pc_data_line.setData(time_data[limit:], pc_data[limit:])
            self.peaks_line.setData(time_data[limit:], peaks[limit:])

class LoopTimer(threading.Thread):
    def __init__(self, interval, function, args=None, kwargs=None):
        super().__init__()
        self.interval = interval
        self.function = function
        self.args = args if args is not None else []
        self.kwargs = kwargs if kwargs is not None else {}
        self.finished = threading.Event()

    def cancel(self):
        """Stop the timer if it hasn't finished yet."""
        self.finished.set()

    def run(self):
        while not self.finished.is_set():
            if not self.finished.wait(self.interval):
                self.function(*self.args, **self.kwargs)

def interval():
    global alarm_timer
    if alarm_timer is None:
        alarm_timer = LoopTimer(3, alarm)
        alarm_timer.start()
    
def alarm():
    contents = urllib.request.urlopen("http://127.0.0.1:1337/vibe/50").read()

# Запускаем http сервер для связи с Pavlok:
p = subprocess.Popen(['node', 'pavlok-srv.js'])
# Подключаемся к Sensor Server для доступа к данным акселерометра смартфона:
sensor = Sensor(address=address, sensor_type="android.sensor.accelerometer")
sensor.connect() # asynchronous call

alarm_timer = None
interval_timer = LoopTimer(20, interval)
interval_timer.start()

app = QtWidgets.QApplication(sys.argv)

print('HIT.1')
# call on Main thread
window = MainWindow()
window.show()

res = app.exec_()

print('HIT.2')
interval_timer.cancel()
if alarm_timer is not None:
    alarm_timer.cancel()

p.terminate()
print('HIT.3')
sys.exit(res)
