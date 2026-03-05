import sqlite3, json

con = sqlite3.connect("registry.sqlite")
row = con.execute("SELECT json_blob FROM documents WHERE doc_id = 'doc_ff615c3dc79f'").fetchone()
con.close()

data = json.loads(row[0])
print(json.dumps(data, indent=2))

