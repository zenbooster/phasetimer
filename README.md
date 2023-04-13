# PHASETIMER - интервальный таймер для практики фазы, с возможностью отключения сигналов дыханием.

PHASETIMER сам активируется, когда вы достанете наушники, и деактивируется, когда вы уберёте их обратно в чехол.

На данный момент нет определения фазы БДГ, но есть подбуживание синтезированным голосом громкость которого с каждым разом нарастает до тех пор, пока будильник не будет отключен двойным выдохом (Быстрые вдох-выдох, вдох-выдох в течении секунды).
Реализован прямой и непрямой методы. На данный момент, сначала включается режим "прямой метод". Он состоит из interval_dir_cnt будильников, каждый из которых срабатывает каждые interval_dir_period секунд. После, запускается режим "непрямой метод", будильники в котором срабатывают каждые interval_ndir_period секунд. При срабатывании будильника, скриптом будет произнесена одна из нескольких фраз подбуживания. Фразы будут повторяться каждые alarm_period секунд.

Чтобы испытать на себе действие скрипта, нужно:
1. Смартфон на базе Android и компьютер с Linux (я использовал Raspberry PI 4b с Ubuntu 22.04 LTS без иксов) в одной WiFi сети. Также, понадобятся Bluetooth наушники.
2. Склонировать этот репозиторий на Linux.
3. Настроить PulseAudio для работы в режиме System-Wide.
4. Выполнить сопряжение Bluetooth наушников с неттопом (используйте bluetoothctl).
5. Установить службы из репозитория; phasetimer-guardian.service должен запускаться вместе с системой.
6. Установить на Android смартфоне приложение umer0586/SensorServer из playmarket-а.
7. Запустить SensorServer на смартфоне (в настройках указать sampling rate: 40000 микросекунд, что соответствует 25 герцам указанным в скрипте) и вбить IP адрес который он сообщит в скрипт, в переменную address класса TMyApplication, в формате, который там предлагается. Желательно настроить dhcp сервер таким образом, чтобы смартфон каждый раз получал один и тот же IP адрес.
8. Осталось вставить наушники и лечь спать на спину, положив смартфон на грудь, в районе мечевидного отростка или чуть ниже ;)

Автор испытал действие на себе, и может сообщить, что если к обычному аудио-файлу с одиночными будильниками на фоне тишины вскоре вырабатывается привыкание и его просто не слышишь, то к этому скрипту привыкания не будет. После короткой тренировки будильники легко получается отключать дыханием, и выполнять практику.

В планах:
- жду компактный Bluetooth акселерометр, чтобы крепить его на магните к футболке или к телу (2-й магнит под пластырем).
