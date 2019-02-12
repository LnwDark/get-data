#!/usr/bin/python
from zk import ZK, const
import sqlite3
import requests

# CONFIG TID
TID = 3452

# TID = 4812
# TID = 5180
# TID = 6298
ZktIP = '192.168.100.10'
#1840

# CRON 60sec
# Read                                  - Done
# Insert to SQLite - Status = 0         - SQLite
# Delete Record In ZKT                  - Done
# Disconnect ZKT                        - Done

# Loop Select DB                        - SQLite
# Push To App.nextschool.IO Return OK   - HTTP
# Delete Local DB Return OK Record      - SQLite

# Insert to SQLite - Status = 0         - SQLite


db = sqlite3.connect('./mydb')
with db:
        cur = db.cursor()
        cur.execute("CREATE TABLE if not exists logs (created_at TEXT,user_id INT)")

def insertToDb(db, a):
    cursor = db.cursor()
    cur.execute('''INSERT INTO logs(created_at, user_id)
        VALUES(?,?)''', (a.timestamp,a.user_id))
    db.commit()

def sendHTTP(created_at, user_id):
    url = 'https://app.nextschool.io/api/zkt-teacher-clock' # Set destination URL here
    payload = {'created_at': created_at,'emp_no' : user_id,'tid' : TID}     # Set POST fields here
    try:
        response = requests.post(url, data=payload)
        json = response.json()
        print(response.text)
        if json['status'] == 'ok':
            return True
        if json['status'] == 'fail' and json['error'].find("Emp") > -1:
            return True
    except requests.exceptions.RequestException as e:
        print(e)

    return False

def sendCheck():
    url = 'https://app.nextschool.io/api/zkt-check' # Set destination URL here
    payload = {'tid' : TID}     # Set POST fields here
    try:
        response = requests.post(url, data=payload)
        print(response.text)
    except requests.exceptions.RequestException as e:
        print(e)

def selectFromDb(db):
    cursor = db.cursor()
    cursor.execute('''SELECT * FROM logs''')
    return cursor.fetchall()

def readZKT(db):    
    conn = None
    attendances = None
    zk = ZK(ZktIP, port=4370, timeout=10)
    try:
        print('Connecting to device ...')
        conn = zk.connect()
        # print('Disabling device ...')
        # conn.disable_device()
        # print('Firmware Version: : {}'.format(conn.get_firmware_version()))
        # print '--- Get User ---'
        # users = conn.get_users()
        # i = 0
        # for user in users:
        #     i += 1
        #     privilege = 'User'
        #     if user.privilege == const.USER_ADMIN:
        #         privilege = 'Admin'
        
        #     print '- UID #{}'.format(user.uid)
        #     print '  Name       : {}'.format(user.name)
        #     print '  Privilege  : {}'.format(privilege)
        #     print '  Password   : {}'.format(user.password)
        #     print '  Group ID   : {}'.format(user.group_id)
        #     print '  User  ID   : {}'.format(user.user_id)

        # print('Total Teacher: ', i)

        print('Getting attendances')
        attendances = conn.get_attendance()

        # for a in attendances:
            # print '- UserID #{}'.format(a.user_id)
            # print '  Timestamp #{}'.format(a.timestamp)
            # print '  Status #{}'.format(a.status)

        # print('Clear Attendance')
        # Clear attendances record
        if len(attendances) > 0:
            conn.clear_attendance()
            for a in attendances:
                if not sendHTTP(a.timestamp, a.user_id):
                    insertToDb(db, a)

        # print("Voice Test ...")
        # conn.test_voice()
        # print('Enabling device ...')
        # conn.enable_device()

    except Exception as e:
        print("Process terminate : {}".format(e))
    finally:
        if conn:
            conn.disconnect()

    return attendances

readZKT(db)
for row in selectFromDb(db):
    # row[0] returns the first column in the query (name), row[1] returns email column.
    print('{0} : {1}'.format(row[0], row[1]))
    # Send HTTP
    if sendHTTP(row[0],row[1]):
        # Delete Record
        print("Delete logs where created_at={} and user_id={}".format(
            row[0],row[1]
        ))
        c = db.cursor()
        c.execute('DELETE FROM logs WHERE created_at=? and user_id=?', (row[0],row[1],))
        db.commit()
db.close()

sendCheck()