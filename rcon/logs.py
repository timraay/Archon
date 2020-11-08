import sqlite3
from datetime import datetime
from io import StringIO

db = sqlite3.connect("instances.db")
cur = db.cursor()
cur.execute('CREATE TABLE IF NOT EXISTS logs(instance_id INT, log_id INT, category TEXT, message TEXT, timestamp TEXT, FOREIGN KEY (instance_id) REFERENCES instances(instance_id))')
db.commit()


class ServerLogs:
    def __init__(self, instance_id):
        self.id = instance_id

        cur.execute('SELECT instance_id FROM instances WHERE instance_id = ?', (self.id,))
        res = cur.fetchone()
        if not res:
            from rcon.instances import UnknownInstanceError
            raise UnknownInstanceError("No instance found with ID %s" % self.id)
            
    def _parse_logs(self, res, reverse=False):
        logs = []
        for row in sorted(res, key=lambda x: x[0], reverse=reverse):
            log = {
                "category": row[1],
                "message": row[2],
                "timestamp": datetime.strptime(row[3], "%Y-%m-%d %H:%M:%S.%f")
            }
            logs.append(log)
        return logs

    def get_logs(self, category=None, limit=50, reverse=False):
        if category: cur.execute('SELECT log_id, category, message, timestamp FROM logs WHERE instance_id = ? AND category = ? ORDER BY log_id DESC LIMIT ?', (self.id, category, limit))
        else: cur.execute('SELECT log_id, category, message, timestamp FROM logs WHERE instance_id = ? ORDER BY log_id DESC LIMIT ?', (self.id, limit))
        res = cur.fetchall()
        logs = self._parse_logs(res, reverse)
        return logs

    def add(self, category: str, messages):
        if not isinstance(messages, (list, tuple)):
            messages = [str(messages)]
        
        cur.execute('SELECT MAX(log_id) FROM logs WHERE instance_id = ?', (self.id,))
        res = cur.fetchone()
        log_id = res[0] if res[0] != None else 0

        time = datetime.now()
        timestamp = str(time)

        for message in messages:
            log_id += 1
            cur.execute('INSERT INTO logs VALUES (?,?,?,?,?)', (self.id, log_id, category, message, timestamp))
            print(f"[{time.strftime('%H:%M')}] [{category.upper()}] {message}")
        delete_old_logs()
        db.commit()
    
    def export(self):
        f = StringIO()
        logs = self.get_logs(limit=999)
        f.write("\n".join([format_log(log) for log in logs]))
        f.seek(0)
        return f


def format_log(log):
    timestamp = log['timestamp']
    date = timestamp.strftime("%d-%m")
    time = timestamp.strftime("%H:%M")
    category = log['category'].upper()
    message = log['message']
    return f"[{date}] [{time}] [{category}] {message}"


def delete_old_logs():
    cur.execute("DELETE FROM logs WHERE timestamp < DATETIME('NOW', '-5 days')")
    db.commit()