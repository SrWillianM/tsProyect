import sqlite3

conn = sqlite3.connect('db.sqlite3')
for row in conn.execute('SELECT sql FROM sqlite_master WHERE type="table" AND sql IS NOT NULL'):
    print(row[0] + ";\n")
conn.close()
