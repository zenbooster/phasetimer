#!/usr/bin/env python3
# Toggles headset connection
import logging
from systemd.journal import JournalHandler
import dbus
from gi.repository import GLib
from dbus.mainloop.glib import DBusGMainLoop
import subprocess
import re

class TMyApplication:
  # Bits: 21=SvcClass::Audio, 18=SvcClass::Rendering, 10=MajClass::Audio_Video
  bt_dev_class_mask = 0x240400
  slave_svc = 'phasetimer.service'

  def _signal_handler(self, *args, **kwargs):
    if args[0] == 'org.bluez.MediaControl1':
      path = kwargs['path']
      m = self.mac_prog.search(path)
      if m:
        mac = m.group(0)

        if mac in self.dev_id:
          if args[1]['Connected']:
            log.info(f'{mac} connected')
            self.i_connected += 1
          else:
            log.info(f'{mac} disconnected')
            self.i_connected -= 1

          svc = TMyApplication.slave_svc
          if not self.i_connected_old and self.i_connected:
            log.info(f'start {svc}')
            subprocess.run(f'systemctl start {svc}', shell=True)

          if self.i_connected_old and not self.i_connected:
            log.info(f'stop {svc}')
            subprocess.run(f'systemctl stop {svc}', shell=True)

          self.i_connected_old = self.i_connected

  def __init__(self):
    # get list of paired devices:
    res = subprocess.run("bluetoothctl paired-devices | grep -oE '([[:xdigit:]]{2}:){5}[[:xdigit:]]{2}'", shell=True, capture_output=True)
    res = res.stdout.decode()
    if not len(res):
      raise Exception('Unable to find paired bluetooth devices!')

    res = res.splitlines()
    self.dev_id = set()

    for line in res:
      mac = line
      # get bluetooth device class info:
      res = subprocess.run(f"bluetoothctl info {mac} | grep Class | grep -oE '0x[[:xdigit:]]+'", shell=True, capture_output=True)
      res = res.stdout.decode()
      cls = int(res[:-1], 0)

      # check device class:
      if cls & TMyApplication.bt_dev_class_mask == TMyApplication.bt_dev_class_mask:
        if not len(self.dev_id):
          log.info(f'Found paired audio rendering bluetooth device(s) with:')

        log.info(f'  mac={mac}; class={hex(cls)}')
        self.dev_id.add(mac.replace(':', '_'))

    self.i_connected = 0
    self.i_connected_old = 0
    self.mac_prog = re.compile(r'([0-9a-f]{2}_){5}[0-9a-f]{2}', re.I | re.S)

  def run(self):
    DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()
    #register your signal callback
    bus.add_signal_receiver(self._signal_handler,
                        bus_name='org.bluez',
                        interface_keyword='interface',
                        member_keyword='member',
                        path_keyword='path',
                        message_keyword='msg')
    loop = GLib.MainLoop()
    loop.run()

log = logging.getLogger('phasetimer')
log.addHandler(JournalHandler())
log.setLevel(logging.INFO)

try:
  app = TMyApplication()
  app.run()
except Exception as err:
  log.error(f'Unexpected {err=}, {type(err)=}')
  exit(1)
