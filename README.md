# DroSeCl - Droid Sensor Client (пока что используется такое кодовое название)
Изначально - тестовый клиент для umer0586/SensorServer. Использовался для анализа респираторной активности.
<image align="left" src="https://github.com/zenbooster/drosecl/blob/main/doc/16012023.jpg?raw=true">
Сейчас это уже будильник для практики осознанных снов. На данный момент нет определения фазы БДГ, но есть подбуживание синтезированным голосом громкость которого с каждым разом нарастает до тех пор, пока будильник не будет отключен двойным выдохом (Быстрые вдох-выдох, вдох-выдох в течении секунды).
Реализован прямой и непрямой методы. На данный момент, сначала включается режим "прямой метод". Он состоит из interval_dir_cnt будильников, каждый из которых срабатывает каждые interval_dir_period секунд. После, запускается режим "непрямой метод", будильники в котором срабатывают каждые interval_ndir_period секунд. При срабатывании будильника, скриптом будет произнесена одна из нескольких фраз подбуживания. Фразы будут повторяться каждые alarm_period секунд.

Чтобы испытать на себе действие скрипта, нужно:
1. Смартфон на базе Android и компьютер с Linux (я использовал безвентиляторный неттоп с Ubuntu 22.04 LTS) в одной WiFi сети. При желании, можно использовать беспроводные наушники.
2. Склонировать этот репозиторий на Linux.
3. Установить на Android смартфоне приложения umer0586/SensorServer и "Simple Protocol Player" из playmarket-а.
4. Запустить SensorServer на смартфоне и вбить IP адрес который он сообщит в скрипт, в переменную address класса TMyApplication, в формате, который там предлагается.

5*. Запустить на Linux, в отдельном окне терминала, в фоне, или оформить в виде службы команду для запуска аудио-сервера:

`ncat -lk -p 48000 -c "pacat -vv -r -d `pactl info | grep -oP 'Default Sink: \K.+'` --rate=48000 --channels=2 --format=s16le"`

6. Запустить на смартфоне Simple Protocol Player или подобную программу, указав адрес и порт аудио-сервера и параметры воспроизводимого аудио-потока.
7. Запустить скрипт main.py и лечь спать на спину, положив смартфон на грудь, в районе мечевидного отростка или чуть ниже ;)

Автор испытал действие на себе, и может сообщить, что если к обычному аудио-файлу с одиночными будильниками на фоне тишины вскоре вырабатывается привыкание и его просто не слышишь, то к этому скрипту привыкания не будет. После короткой тренировки будильники легко получается отключать дыханием, и выполнять практику.

\* \- В pulseaudio версий 15.99 и 16.0, в утилите pacat есть баг, в результате которого, через несколько часов работы вылезет что-то вроде этого:
`Assertion 'size < (1024*1024*96)' failed at pulse/xmalloc.c:83, function pa_xrealloc()`

Чтобы исправить эту ситуацию, мною был выпущен фикс, который в данный момент находится на рассмотрении:
https://gitlab.freedesktop.org/pulseaudio/pulseaudio/-/merge_requests/770

Но патч можно применить уже сейчас, скачав исходники pulseaudio:
```
From 085b2ba0e2a61d12a27bc66560c1b8d5bde1d8a5 Mon Sep 17 00:00:00 2001
From: =?UTF-8?q?=D0=98=D0=BB=D1=8C=D1=8F?= <zenbooster@gmail.com>
Date: Sun, 22 Jan 2023 21:20:03 +0000
Subject: [PATCH 1/3] fixed "Assertion 'size < (1024*1024*96)' failed at
pulse/xmalloc.c:83, function pa_xrealloc()"

---
src/utils/pacat.c | 51 ++++++++++++++++++++++++++++++-----------------
1 file changed, 33 insertions(+), 18 deletions(-)

diff —git a/src/utils/pacat.c b/src/utils/pacat.c
index e656dee1b..80972b5cb 100644
-— a/src/utils/pacat.c
+++ b/src/utils/pacat.c
@@ -44,6 +44,7 @@
#include <pulsecore/macro.h>
#include <pulsecore/sndfile-util.h>
#include <pulsecore/sample-util.h>
+#include <sys/queue.h>

#define TIME_EVENT_USEC 50000

@@ -73,8 +74,14 @@ static void *partialframe_buf = NULL;
static size_t partialframe_len = 0;

/* Recording Mode buffers */
-static void *buffer = NULL;
-static size_t buffer_length = 0, buffer_index = 0;
+struct buffer_t {
+ void *buffer;
+ size_t length;
+ SIMPLEQ_ENTRY(buffer_t) next;
+};
+
+SIMPLEQ_HEAD(buffer_queue_t, buffer_t);
+struct buffer_queue_t buffer_head;

static void *silence_buffer = NULL;
static size_t silence_buffer_length = 0;
@@ -251,13 +258,16 @@ static void stream_read_callback(pa_stream *s, size_t length, void *userdata) {
/* If there is a hole in the stream, we generate silence, except
* if it's a passthrough stream in which case we skip the hole. */
if (data || !(flags & PA_STREAM_PASSTHROUGH)) {
- buffer = pa_xrealloc(buffer, buffer_index + buffer_length + length);
+ void *buffer = pa_xmalloc(length);
if (data)
- memcpy((uint8_t *) buffer + buffer_index + buffer_length, data, length);
+ memcpy((uint8_t *) buffer, data, length);
else
- pa_silence_memory((uint8_t *) buffer + buffer_index + buffer_length, length, &sample_spec);
+ pa_silence_memory((uint8_t *) buffer, length, &sample_spec);

- buffer_length += length;
+ struct buffer_t *buf = pa_xmalloc(sizeof(struct buffer_t));
+ buf->buffer = buffer;
+ buf->length = length;
+ SIMPLEQ_INSERT_TAIL(&buffer_head, buf, next);
}

pa_stream_drop(s);
@@ -594,14 +604,16 @@ static void stdout_callback(pa_mainloop_api*a, pa_io_event *e, int fd, pa_io_eve
pa_assert(e);
pa_assert(stdio_event == e);

- if (!buffer) {
+ if (SIMPLEQ_EMPTY(&buffer_head)) {
mainloop_api->io_enable(stdio_event, PA_IO_EVENT_NULL);
return;
}

- pa_assert(buffer_length);
+ struct buffer_t *buf = SIMPLEQ_FIRST(&buffer_head);
+ void *buffer = buf->buffer;
+ size_t length = buf->length;

- if ((r = pa_write(fd, (uint8_t*) buffer+buffer_index, buffer_length, userdata)) <= 0) {
+ if ((r = pa_write(fd, (uint8_t*) buffer, length, userdata)) <= 0) {
pa_log(_("write() failed: %s"), strerror(errno));
quit(1);

@@ -610,14 +622,9 @@ static void stdout_callback(pa_mainloop_api*a, pa_io_event *e, int fd, pa_io_eve
return;
}

- buffer_length -= (uint32_t) r;
- buffer_index += (uint32_t) r;
-
- if (!buffer_length) {
- pa_xfree(buffer);
- buffer = NULL;
- buffer_length = buffer_index = 0;
- }
+ pa_xfree(buffer);
+ SIMPLEQ_REMOVE_HEAD(&buffer_head, next);
+ pa_xfree(buf);
}

/* UNIX signal to quit received */
@@ -780,6 +787,8 @@ int main(int argc, char *argv[]) {
{NULL, 0, NULL, 0}
};

+ SIMPLEQ_INIT(&buffer_head);
+
setlocale(LC_ALL, "");
#ifdef ENABLE_NLS
bindtextdomain(GETTEXT_PACKAGE, PULSE_LOCALEDIR);
@@ -1247,7 +1256,13 @@ quit:
}

pa_xfree(silence_buffer);
- pa_xfree(buffer);
+ while(!SIMPLEQ_EMPTY(&buffer_head)) {
+ struct buffer_t *buf = SIMPLEQ_FIRST(&buffer_head);
+ pa_xfree(buf->buffer);
+ SIMPLEQ_REMOVE_HEAD(&buffer_head, next);
+ pa_xfree(buf);
+ }
+
pa_xfree(partialframe_buf);

pa_xfree(server);
—
GitLab

From a1950c3c48d657957fcd7c43b30496c1737260ce Mon Sep 17 00:00:00 2001
From: ZenBooster <zenbooster@gmail.com>
Date: Mon, 23 Jan 2023 12:46:35 +0300
Subject: [PATCH 2/3] stdout_callback: since the function 'pa_write' may not
write all the data we asked it to, we will add an index field to each element
of the queue.

---
src/utils/pacat.c | 19 +++++++++++++------
1 file changed, 13 insertions(+), 6 deletions(-)

diff —git a/src/utils/pacat.c b/src/utils/pacat.c
index 80972b5cb..0646b670c 100644
-— a/src/utils/pacat.c
+++ b/src/utils/pacat.c
@@ -77,6 +77,7 @@ static size_t partialframe_len = 0;
struct buffer_t {
void *buffer;
size_t length;
+ size_t index;
SIMPLEQ_ENTRY(buffer_t) next;
};

@@ -267,6 +268,7 @@ static void stream_read_callback(pa_stream *s, size_t length, void *userdata) {
struct buffer_t *buf = pa_xmalloc(sizeof(struct buffer_t));
buf->buffer = buffer;
buf->length = length;
+ buf->index = 0;
SIMPLEQ_INSERT_TAIL(&buffer_head, buf, next);
}

@@ -610,8 +612,8 @@ static void stdout_callback(pa_mainloop_api*a, pa_io_event *e, int fd, pa_io_eve
}

struct buffer_t *buf = SIMPLEQ_FIRST(&buffer_head);
- void *buffer = buf->buffer;
- size_t length = buf->length;
+ void *buffer = buf->buffer + buf->index;
+ size_t length = buf->length - buf->index;

if ((r = pa_write(fd, (uint8_t*) buffer, length, userdata)) <= 0) {
pa_log(_("write() failed: %s"), strerror(errno));
@@ -621,10 +623,15 @@ static void stdout_callback(pa_mainloop_api*a, pa_io_event *e, int fd, pa_io_eve
stdio_event = NULL;
return;
}
-
- pa_xfree(buffer);
- SIMPLEQ_REMOVE_HEAD(&buffer_head, next);
- pa_xfree(buf);
+
+ buf->index += r;
+
+ if (buf->index == buf->length)
+ {
+ pa_xfree(buffer);
+ SIMPLEQ_REMOVE_HEAD(&buffer_head, next);
+ pa_xfree(buf);
+ }
}

/* UNIX signal to quit received */
—
GitLab

From b601bfd6f66e0b9ec9d7f4c9f7858fdcad5c0f32 Mon Sep 17 00:00:00 2001
From: ZenBooster <zenbooster@gmail.com>
Date: Mon, 23 Jan 2023 13:49:38 +0300
Subject: [PATCH 3/3] fix coding style

---
src/utils/pacat.c | 3 +--
1 file changed, 1 insertion(+), 2 deletions(-)

diff —git a/src/utils/pacat.c b/src/utils/pacat.c
index 0646b670c..6b10ea07e 100644
-— a/src/utils/pacat.c
+++ b/src/utils/pacat.c
@@ -626,8 +626,7 @@ static void stdout_callback(pa_mainloop_api*a, pa_io_event *e, int fd, pa_io_eve

buf->index += r;

- if (buf->index == buf->length)
- {
+ if (buf->index == buf->length) {
pa_xfree(buffer);
SIMPLEQ_REMOVE_HEAD(&buffer_head, next);
pa_xfree(buf);
—
GitLab
```
