# coding: utf-8

import subprocess
import shlex
import os
import sys
import sqlite3
import datetime
import time
import json


try:
    file_settings = open("settings.json")
    s = file_settings.read()
    file_settings.close()
    settings = json.loads(s)

    YA_USER = settings["YA_USER"]
    YA_PASS = settings["YA_PASS"]

    SCRIPT_FILE = settings["SCRIPT_FILE"]
    NAME_FILE = settings["NAME_FILE"]
    NAME_FILE_LOG = settings["NAME_FILE_LOG"]

    TIME_EMAIL_START = datetime.timedelta(hours=settings["TIME_EMAIL_START"])
    TIME_EMAIL_END = datetime.timedelta(hours=settings["TIME_EMAIL_END"])

    TIME_BACKUP_START = datetime.timedelta(hours=settings["TIME_BACKUP_START"])
    TIME_BACKUP_END = datetime.timedelta(hours=settings["TIME_BACKUP_END"])

    SMTP_SERVER = settings["SMTP_SERVER"]
    DESTINATION = settings["DESTINATION"]
    SUBJECT_EMAIL = settings["SUBJECT_EMAIL"]

    INIZIALIZED = True

except:
    INIZIALIZED = False


def update_base():
    try:
        conn = sqlite3.connect('main.db')
        conn.execute("CREATE TABLE register ("
                     "id INTEGER PRIMARY KEY AUTOINCREMENT,"  # id записи в БД
                     "datebackup TEXT)")
        conn.execute("CREATE TABLE logs ("
                     "id INTEGER PRIMARY KEY AUTOINCREMENT,"  # id записи в БД
                     "datebackup TEXT,"
                     "state INTEGER DEFAULT 0,"
                     "desc TEXT)")
        conn.close()
    except:
        pass


def check_backuper():
    try:
        conn = sqlite3.connect('main.db')
        c = conn.cursor()
        c.execute("SELECT id FROM register WHERE datebackup = :datebackup;",
                  {'datebackup': datetime.datetime.today().strftime("%d.%m.%Y")})
        result = c.fetchall()
        conn.close()
        return len(result)
    except:
        return 0


def add_record_register():
    conn = sqlite3.connect('main.db')
    c = conn.cursor()
    c.execute("INSERT INTO register (datebackup) VALUES (:datebackup);",
              {'datebackup': datetime.datetime.today().strftime("%d.%m.%Y")})
    conn.commit()
    conn.close()


def add_record_logs(desc):
    conn = sqlite3.connect('main.db')
    c = conn.cursor()
    c.execute("INSERT INTO logs (datebackup, state, desc) VALUES (:datebackup, 0, :desc);",
              {'datebackup': datetime.datetime.today().strftime("%d.%m.%Y"), 'desc': desc})
    conn.commit()
    conn.close()


def backup():
    isfile = os.path.exists(NAME_FILE + ".dt")
    if isfile:
        new_name_file = NAME_FILE + " " + str(datetime.datetime.today().strftime("%d_%m_%Y %H_%M_%S")) + ".dt"
        os.rename(NAME_FILE + ".dt", new_name_file)

    args = shlex.split(SCRIPT_FILE)
    p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    p.communicate()

    if os.path.exists(NAME_FILE + ".dt"):
        add_record_register()
        new_name_file = NAME_FILE + " " + str(datetime.datetime.today().strftime("%d_%m_%Y %H_%M_%S")) + ".dt"
        os.rename(NAME_FILE + ".dt", new_name_file)

        try:
            from YaDiskClient import YaDisk
            disk = YaDisk(YA_USER, YA_PASS)
            disk.upload(new_name_file, '/' + new_name_file)
        except:
            add_record_logs(u'Ошибка отправки файла на Яндекс.Диск')

    if os.path.exists(NAME_FILE_LOG + ".txt"):
        try:  # TODO доделать
            f = open(NAME_FILE_LOG + ".txt")
            r = f.read().decode('windows-1251')
            f.close()
            add_record_logs(r)
            os.remove(NAME_FILE_LOG + ".txt")
        except:
            pass


def send_email(content):
    if content == "":
        return False

    destination = [DESTINATION]

    # typical values for text_subtype are plain, html, xml
    text_subtype = 'plain'

    from smtplib import SMTP_SSL as SMTP       # this invokes the secure SMTP protocol (port 465, uses SSL)
    from email.mime.text import MIMEText

    try:
        msg = MIMEText(content, text_subtype, "utf-8")
        msg['Subject'] = SUBJECT_EMAIL
        msg['From'] = YA_USER
        msg['To'] = DESTINATION
        conn = SMTP(SMTP_SERVER)
        conn.set_debuglevel(False)
        conn.login(YA_USER, YA_PASS)

        stat = False

        try:
            conn.sendmail(YA_USER, destination, msg.as_string())
            stat = True
        finally:
            conn.close()
    except Exception, exc:
        pass

    return stat


def get_logs():
    conn = sqlite3.connect('main.db')
    c = conn.cursor()
    c.execute("SELECT datebackup, desc FROM logs WHERE state = 0;")
    result = c.fetchall()
    conn.close()

    str_c = ""
    a = "\n################################################\n\n"

    for item in result:
        str_c = str_c + item[0] + "\n" + item[1] + a

    return str_c


def update_logs():
    conn = sqlite3.connect('main.db')
    c = conn.cursor()
    c.execute("UPDATE logs SET state = 1 WHERE state = 0;")
    conn.commit()
    conn.close()


if __name__ == "__main__":
    while True:
        if INIZIALIZED:
            print 'Checked in ' + str(datetime.datetime.today())

            update_base()

            now = datetime.timedelta(hours=datetime.datetime.today().hour)

            if now >= TIME_BACKUP_START or now < TIME_BACKUP_END:
                if check_backuper() == 0:
                    backup()

            if now >= TIME_EMAIL_START or now < TIME_EMAIL_END:
                succsess = send_email(get_logs())
                if succsess:
                    update_logs()

            time.sleep(10)