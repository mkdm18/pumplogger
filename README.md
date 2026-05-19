# Pump Station Logger
![Version](https://img.shields.io/badge/version-1.0-blue)
![Status](https://img.shields.io/badge/status-stable-green)
![Platform](https://img.shields.io/badge/platform-RaspberryPi-orange)

## 📦 1. Download
[Download v1.0](https://github.com/mkdm18/pumplogger/releases/tag/v1.0)

## 📌 2. Overview
Pump Station Logger — автономная система сбора, расчёта и хранения данных насосной станции.  
✔ Работает без интернета  
✔ Автоматический запуск  
✔ Защита от потери данных  
✔ Экспорт на USB  
✔ SMART-аналитика  

## 🚀 3. Version 1.0 (Stable)

### 3.1. Основные возможности
- Расчёт RPM по периоду (DI3)
- Детектор остановки по (DI1)
- Общий литраж и SMART аналитика хранится в БД
- Автоэкспорт на USB
- Авторазмонтирование флешки
- SMART-статистика
- Ротационные backup БД

## 🧠 4. Architecture
```
     ┌────────────────────────────────────────────────────────────────┐
     │              -=Датчики 4-20 мА=-                               │
     │                                                                │    
     │ 1. Давление в манифольде (manifold_pressure_mpa)               │
     │ 2. Температура масла механической части (mech_oil_temp_c)      │
     │ 3. Давление масла механической части (mech_oil_pressure_kpa)   │
     │ 4. Температура гидравлического масла (hydraulic_oil_temp_c)    │
     │ 5. Давление масла АКПП (transmission_oil_pressure_kpa)         │
     │ 6. Температура масла АКПП (transmission_oil_temp_c)            │
     └────┬───────────────────────────────────────────────────────────┘
          ▼                        ┌────────────────────────┐
          │                        │                        │                       
          │                        │                        ▲
┌─────────┴────────┐     ┌─────────┴───────────┐  ┌─────────┴─────────┐                    
│   -=PLC=-        │     │   -=MV210-202=-     │  │    -=Датчик=-     │
│                  │     │       (DI1/DI3)     │  │   AR-LM12-3004PC  │
│Ip: 192.168.117.10│     │ Ip: 192.168.117.45  │  │ PNP НО+НЗ 6…36 В  │
└─────────┬────────┘     └─────────┬───────────┘  └───────────────────┘
          ▼                        ▼
          └─────────┐    ┌─────────┘    
                    │    │         
                    ▼    ▼
          ┌─────────────────────────────┐
          │ -=RaspberryPi4 + SSD=-      │
          │    app.py                   │      
          │ Ip: 192.168.117.55 (eth0)   │
          │                             │   
          │ -=WiFi=-                    │
          │ SSID: omega26               │
          │ PSK ******************      │     
          └───────────┬─────────────────┘
                      │
          ┌───────────┴────────────┐
          ▼                        ▼
          SQLite              USB Export
          (data.db)           (CSV files)
```

## 5. Комплектующие:
RaspberryPi4 + SSD:
* Микрокомпьютер Raspberry Pi 4 model B 4Gb
* 256 ГБ Внешний SSD DEXP W500C
MV210-202: 
* ОВЕН МВ210-202 Номер: 67615180132025225 
Датчик:
* Индуктивный бесконтактныей датчики AR-LM12-3004PC 

## 6. Recommended Raspberry Pi OS
Рекомендуется использовать:
Raspberry Pi OS Lite 64-bit
Без GUI/Desktop environment.

## 🔧 7. Raspberry Pi System Preparation (Recommended Before Installation)

### 7.1. Update Raspberry Pi OS
```bash
     sudo apt update 
     sudo apt upgrade -y 
     sudo apt install mc htop sysstat smartmontools -y
     sudo reboot
```

### 7.2. Disable UAS mode for USB SSD
Некоторые USB-SATA bridge контроллеры (особенно JMicron) вызывают:
* random I/O errors
* USB reset
* boot freeze
* EXT4 recovery
* unstable SQLite behavior
Проверь USB bridge:
```bash
     lsusb
```
Пример: `152d:0901 JMicron Technology Corp.`  
Открой boot cmdline:
```bash
     sudo mcedit /boot/firmware/cmdline.txt
```
В конец строки добавить: `usb-storage.quirks=152d:0901:u`  
После reboot, выполни
```bash
     lsusb -t
```
Ожидается: `Driver=usb-storage` а НЕ: `Driver=uas`  
SSD должен работать через Driver=usb-storage:

### 7.3. Configure Stable HDMI Mode
Рекомендуется отключить полный KMS graphics stack.
Открой:
```bash
     sudo mcedit /boot/firmware/config.txt
```
Измени строк `dtoverlay=XXX-XXX-v3d`  на `dtoverlay=disable-v3d`  
Добавь:  
``` 
hdmi_force_hotplug=1
hdmi_group=2
hdmi_mode=82
```
Это:
* предотвращает потерю HDMI сигнала
* отключает проблемный vc4 DRM/KMS stack
* фиксирует стабильный HDMI режим 1920x1080@60Hz

### 7.4. Verify Power Stability
После первого boot выполни: `vcgencmd get_throttled`    
Нормальное состояние: `throttled=0x0`  
Недостаток питания регистрируется с момента последне загрузки.  
Следует после отладки системы проверить значения вновь.  

### 7.5. Verify SSD Health
Проверить SSD:
```bash
     sudo smartctl -a -d sat /dev/sda
```
Убедись что:
```
Reallocated_Sector_Ct = 0
Current_Pending_Sector = 0
Offline_Uncorrectable = 0
```

### 7.6. Disable SMART daemon (optional)
USB SSD bridge устройства часто вызывают `failed state smartmontools.service.`  
рекомендуется:
```bash
sudo systemctl disable smartmontools.service
sudo systemctl stop smartmontools.service
sudo systemctl reset-failed
```
SMART при этом остаётся доступен вручную через smartctl.

## 📦 8. Installation
Перед началом: архив `pumplogger_v1.0.zip` уже должен лежать на Raspberry, например в `/home/user`zxv.
### 8.1. Разархифировать проект во временную папку
```bash
     unzip pumplogger_v1.0.zip -d /home/user/pump_release_tmp
```

### 8.2. Создать папку проекта
```bash
     sudo mkdir -p /opt/pump_station 
     sudo mkdir -p /opt/pump_station/data
     sudo mkdir -p /opt/pump_station/logs
     sudo chown -R user:user /opt/pump_station #Назначить права для пользователя на папку
     cp -a /home/user/pump_release_tmp/starter_project/. /opt/pump_station/ #Скопировать проект
     cd /opt/pump_station #Перейти в папку с проектом
```

### 8.3. Установка зависимостей
```bash
     sudo apt update
     sudo apt install -y python3-venv python3-pip sqlite3 usbutils exfatprogs ntfs-3g
     python3 -m venv /opt/pump_station/venv  
     source /opt/pump_station/venv/bin/activate
     pip install --upgrade pip
     pip install pymodbus python-snap7
```

### 8.4. Проверка зависимостей
```bash
     cd /opt/pump_station
     source venv/bin/activate
     python - <<'PY'
     import pymodbus
     import snap7
     print("imports ok")
     PY
```

### 8.5. Инициализировать БД
```bash
     cd /opt/pump_station
     source venv/bin/activate
     python - <<'PY'
     from storage import initialize_database
     initialize_database()
     print("DB initialized")
     PY
     sqlite3 /opt/pump_station/data/main.db ".tables" 
```
Ожидаются таблицы: 
```text
     meta_state, 
     board_log, 
     work_log, 
     system_log, 
     usb_export_log, 
     smart_counters
```

### 8.6 Включить WAL mode для SQLite (рекомендуется)
Открыть модель работы с Базой данных
```bash     
     sudo mcedit /opt/pump_station/db.py
```
Найти создание SQLite connection:
```bash
     self.conn = sqlite3.connect(
         db_path,
         timeout=10,
         check_same_thread=False
     )
```
Сразу после добавить :
```bash
     self.conn.execute("PRAGMA journal_mode=WAL;")
     self.conn.execute("PRAGMA synchronous=NORMAL;")
     self.conn.execute("PRAGMA busy_timeout=30000;")
```
Проверить что WAL включился:
```bash
     sqlite3 /opt/pump_station/data/main.db "PRAGMA journal_mode;"
```
Ожидается: wal
WAL mode уменьшает:
* database is locked
* fsync stalls
* SQLite write contention
* вероятность повреждения БД при интенсивной записи

### 8.7 ♻️ Restore Existing Database (Optional)
Если остались БД от предыдущей установки, их можно использовать повторно.
Поддерживаются:
* main.db
* main_backup_a.db
* main_backup_b.db

#### 8.7.1. Остановить сервис
```bash 
     sudo systemctl stop pump_station.service
```

#### 8.7.2. Скопировать старые БД
Например с USB SSD:
```bash
     sudo cp /media/oldssd/main.db /opt/pump_station/data/
     sudo cp /media/oldssd/main_backup_a.db /opt/pump_station/data/
     sudo cp /media/oldssd/main_backup_b.db /opt/pump_station/data/
```

#### 8.7.3. Назначить права
```bash
     sudo chown user:user /opt/pump_station/data/*.db
```

#### 8.7.4. Проверить целостность SQLite
```bash
     sqlite3 /opt/pump_station/data/main.db "PRAGMA integrity_check;"
```
Ожидается:
```text
     ok
```

#### 8.7.5. Проверить таблицы
```bash
     sqlite3 /opt/pump_station/data/main.db ".tables"
```
Ожидаются:
```text
     meta_state
     board_log
     work_log
     system_log
     usb_export_log
     smart_counters
```

#### 8.7.6. Проверить WAL mode
```bash
     sqlite3 /opt/pump_station/data/main.db "PRAGMA journal_mode;"
```
Если НЕ `wal`, открыть:
```bash
     sudo mcedit /opt/pump_station/db.py
```
и убедиться что после sqlite3.connect(...) добавлены:
```python
     self.conn.execute("PRAGMA journal_mode=WAL;")
     self.conn.execute("PRAGMA synchronous=NORMAL;")
     self.conn.execute("PRAGMA busy_timeout=30000;")
```

#### 8.7.7. Запустить сервис
```bash
     sudo systemctl start pump_station.service
```

#### 8.7.8. Проверить запуск
```bash
     systemctl status pump_station.service
```
и:
```bash
     journalctl -u pump_station.service -n 50 --no-pager
```

#### 8.7.9. Проверить последние данные
```bash
     sqlite3 -header -column /opt/pump_station/data/main.db "
     SELECT
     datetime(timestamp_utc,'unixepoch'),
     pump_total_liters
     FROM work_log
     ORDER BY id DESC
     LIMIT 5;
     "
```

#### 8.7.10. Если main.db повреждена
Попробовать backup:
```bash
     cp /opt/pump_station/data/main_backup_a.db /opt/pump_station/data/main.db
```
или:
```bash
     cp /opt/pump_station/data/main_backup_b.db /opt/pump_station/data/main.db
```

### 8.8. Проверка связности устройств
```bash
     ping -c 2 192.168.117.10 #PLC
     ping -c 2 192.168.117.11 #HMI
     ping -c 2 192.168.117.45 #MV210-202
     nc -zv 192.168.117.45 502 #MV210-202
```

### 8.9. Быстрая проверка времени от МВ210
```bash
     cd /opt/pump_station
     source venv/bin/activate
     python - <<'PY'
     from time_sync import read_owen_utc_datetime
     print(read_owen_utc_datetime().isoformat())
     PY
```

### 8.10. Проверка онлайн-значения МВ210
```bash
     cd /opt/pump_station
     source venv/bin/activate
     python read_mv210_live.py #Проверь: counter, period_ms, pump_rpm, flow_lps, total_l. Остановить — Ctrl+C.
```

### 8.11. Проверить синтаксис проекта
```bash
     cd /opt/pump_station
     source venv/bin/activate
     python -m py_compile \
     app.py \
     config.py \
     calculations.py \
     plc.py \
     mv210.py \
     db.py \
     storage.py \
     backup_manager.py \
     time_sync.py \
     usb_export.py \
     read_mv210_live.py \
     reset_maxima.py
```

### 8.12. Пробный ручной запуск основного приложения
```bash
     sudo /opt/pump_station/venv/bin/python /opt/pump_station/app.py #Подожди 1–2 минуты, затем останови Ctrl+C.
```

### 8.13. Установить systemd сервис
```bash
     sudo cp /home/user/pump_release_tmp/systemd/pump_station.service /etc/systemd/system/pump_station.service
     sudo systemctl daemon-reload
     sudo systemctl enable pump_station.service
     sudo systemctl start pump_station.service
     systemctl status pump_station.service
```

### 8.14. Вспомогательные функции для отладки и проверки работы
#### 8.14.1. Посмотреть значения с датчика кардана “вживую”
```bash
     cd /opt/pump_station
     source venv/bin/activate
     python read_mv210_live.py   #должен показывать period_ms, pump_rpm, flow_lps.  
```

#### 8.14.2. Сброс максимумов
```bash
     cd /opt/pump_station
     source venv/bin/activate
     python reset_maxima.py
```

#### 8.14.3. Проверить таблицу SMART
```bash
     sqlite3 -column -header /opt/pump_station/data/main.db "SELECT key, value_minutes FROM smart_counters ORDER BY key;"
```

#### 8.14.4. Бэкап архивирование всего проекта
```bash
     sudo tar -czvf /home/user/pump_backup_$(date +%F_%H-%M-%S).tar.gz /opt/pump_station /etc/systemd/system/pump_station.service
```

#### 8.14.5. Прочие полезные команды
```bash
     journalctl -u pump_station.service -n 100 --no-pager #Смотреть лог работы, последние 100 строк
     journalctl -u pump_station.service -f #Смотреть лог работы, онлайн
     du -h /opt/pump_station/data/main.db #Размер БД
     du -h /opt/pump_station/data/main_backup_a.db /opt/pump_station/data/main_backup_b.db 2>/dev/null #Размер backup-файлов
     du -sh /opt/pump_station #Общий размер проекта
     du -sh /opt/pump_station/data #Размер папки данных
     df -h #Свободное место на диске
```
#### 8.14.6. Последний system log:
```bash
sqlite3 /opt/pump_station/data/main.db "
SELECT datetime(timestamp_utc,'unixepoch'),
level,event_code,message
FROM system_log
ORDER BY id DESC
LIMIT 20;"
```
#### 8.14.7. Последний work log:
```bash
sqlite3 /opt/pump_station/data/main.db "
SELECT *
FROM work_log
ORDER BY id DESC
LIMIT 5;"
```
#### 8.14.8. Системные события:
```bash
sqlite3 /opt/pump_station/data/main.db "
SELECT
datetime(timestamp_utc,'unixepoch'),
level,
event_code,
message
FROM system_log
ORDER BY id DESC
LIMIT 20;"
```
#### 8.14.9. Последние рабочие данные:
```bash
sqlite3 /opt/pump_station/data/main.db "
SELECT
datetime(timestamp_utc,'unixepoch'),
manifold_pressure_mpa,
pump_rpm,
pump_flow_lps,
pump_total_liters
FROM work_log
ORDER BY id DESC
LIMIT 20;"
```
#### 8.14.10. Последние board данные:
```bash
sqlite3 /opt/pump_station/data/main.db "
SELECT
datetime(timestamp_utc,'unixepoch'),
manifold_pressure_mpa,
mech_oil_pressure_kpa,
mech_oil_temp_c,
transmission_oil_pressure_kpa
FROM board_log
ORDER BY id DESC
LIMIT 20;"
```
#### 8.14.11. Все meta параметры:
```bash
sqlite3 /opt/pump_station/data/main.db "
SELECT * FROM meta_state;"
```

#### 8.14.12. SMART counters
```bash
sqlite3 /opt/pump_station/data/main.db "
SELECT * FROM smart_counters;"
```

#### 8.14.13. Размер таблиц
```bash
sqlite3 /opt/pump_station/data/main.db "
SELECT
'board_log', COUNT(*) FROM board_log
UNION ALL
SELECT 'work_log', COUNT(*) FROM work_log
UNION ALL
SELECT 'system_log', COUNT(*) FROM system_log;"
```

## 🏁 Status
Version 1.0 — стабильная версия  
Готово к эксплуатации
