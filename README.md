# Pump Station Logger
![Version](https://img.shields.io/badge/version-1.0-blue)
![Status](https://img.shields.io/badge/status-stable-green)
![Platform](https://img.shields.io/badge/platform-RaspberryPi-orange)

## 📌 Overview
Pump Station Logger — автономная система сбора, расчёта и хранения данных насосной станции.
✔ Работает без интернета  
✔ Автоматический запуск  
✔ Защита от потери данных  
✔ Экспорт на USB  
✔ SMART-аналитика  

---

## 🚀 Version 1.0 (Stable)

### Основные возможности
- Расчёт RPM по периоду (DI3)
- Детектор остановки по (DI1)
- Общий литраж и SMART аналитика хранится в БД
- Автоэкспорт на USB
- Авторазмонтирование флешки
- SMART-статистика
- Ротационные backup БД

---
## 🧠 Architecture

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
## Комплектующие:
RaspberryPi4 + SSD:
* Микрокомпьютер Raspberry Pi 4 model B 4Gb
* 256 ГБ Внешний SSD DEXP W500C

MV210-202: 
* ОВЕН МВ210-202 Номер: 67615180132025225 

Датчик:
* Индуктивный бесконтактныей датчики AR-LM12-3004PC 




## 📦 Installation
Перед началом: архив pumplogger_v1.0.zip уже должен лежать на Raspberry, например в /home/user.

```bash
     #1. Разархифировать проект во временную папку
     unzip pumplogger_v1.0.zip -d /home/user/pump_release_tmp

     #2. Создать папку проекта
     sudo mkdir -p /opt/pump_station 
     sudo mkdir -p /opt/pump_station/data
     sudo mkdir -p /opt/pump_station/logs
     sudo chown -R user:user /opt/pump_station #Назначить права для пользователя на папку
     cp -a /home/user/pump_release_tmp/starter_project/. /opt/pump_station/ #Скопировать проект
     cd /opt/pump_station #Перейти в папку с проектом

     #3. Установка зависимостей
     sudo apt update
     sudo apt install -y python3-venv python3-pip sqlite3 usbutils exfatprogs ntfs-3g
     python3 -m venv /opt/pump_station/venv  
     source /opt/pump_station/venv/bin/activate
     pip install --upgrade pip
     pip install pymodbus python-snap7

     #4. Проверка зависимостей
     cd /opt/pump_station
     source venv/bin/activate
     python - <<'PY'
```
```python
     import pymodbus
     import snap7
     print("imports ok")
```
```bash
     PY

     #5. Инициализировать БД
     cd /opt/pump_station
     source venv/bin/activate
```
```python
     python - <<'PY'
     from storage import initialize_database
     initialize_database()
     print("DB initialized")
```
```bash
     PY
     sqlite3 /opt/pump_station/data/main.db ".tables" #Ожидаются таблицы: meta_state, board_log, work_log, system_log, usb_export_log, smart_counters.

     #6. Проверка связности устройств
     ping -c 2 192.168.117.10 #PLC
     ping -c 2 192.168.117.11 #HMI
     ping -c 2 192.168.117.45 #MV210-202
     nc -zv 192.168.117.45 502 #MV210-202

     #7. Быстрая проверка времени от МВ210
     cd /opt/pump_station
     source venv/bin/activate
```
```python
     python - <<'PY'
     from time_sync import read_owen_utc_datetime
     print(read_owen_utc_datetime().isoformat())
```
```bash
     PY

     #8. Проверка онлайн-значения МВ210
     cd /opt/pump_station
     source venv/bin/activate
     python read_mv210_live.py #Проверь: counter, period_ms, pump_rpm, flow_lps, total_l. Остановить — Ctrl+C.

     #9. Проверить синтаксис проекта
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

     #10. Пробный ручной запуск основного приложения
     sudo /opt/pump_station/venv/bin/python /opt/pump_station/app.py #Подожди 1–2 минуты, затем останови Ctrl+C.

     #11. Установить systemd сервис
     sudo cp /home/user/pump_release_tmp/systemd/pump_station.service /etc/systemd/system/pump_station.service
     sudo systemctl daemon-reload
     sudo systemctl enable pump_station.service
     sudo systemctl start pump_station.service
     systemctl status pump_station.service

     #12. Посмотреть значения с датчика кардана “вживую”
     cd /opt/pump_station
     source venv/bin/activate
     python read_mv210_live.py   #должен показывать period_ms, pump_rpm, flow_lps.  
     
     #13. Сброс максимумов
     cd /opt/pump_station
     source venv/bin/activate
     python reset_maxima.py

     #14. Проверить таблицу SMART
     sqlite3 -column -header /opt/pump_station/data/main.db "SELECT key, value_minutes FROM smart_counters ORDER BY key;"

     #15. Бэкап архивирование всего проекта
     sudo tar -czvf /home/user/pump_backup_$(date +%F_%H-%M-%S).tar.gz /opt/pump_station /etc/systemd/system/pump_station.service

     #14. Полезные команды
     journalctl -u pump_station.service -n 100 --no-pager #Смотреть лог работы, последние 100 строк
     journalctl -u pump_station.service -f #Смотреть лог работы, онлайн
     du -h /opt/pump_station/data/main.db #Размер БД
     du -h /opt/pump_station/data/main_backup_a.db /opt/pump_station/data/main_backup_b.db 2>/dev/null #Размер backup-файлов
     du -sh /opt/pump_station #Общий размер проекта
     du -sh /opt/pump_station/data #Размер папки данных
     df -h #Свободное место на диске

```

---

## 🏁 Status

Version 1.0 — стабильная версия  
Готово к эксплуатации
