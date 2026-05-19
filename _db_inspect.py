import sys
sys.path.insert(0, 'backend/src')
from db import connect

DB = 'postgresql://postgres:2225427@localhost:5432/liuhecai'
conn = connect(DB)

# 1. fetched_mode_records (actual columns)
print('--- public.fetched_mode_records (modes_id=251) ---')
cur = conn.execute("SELECT * FROM public.fetched_mode_records WHERE modes_id=251 ORDER BY year DESC, term DESC LIMIT 3")
for r in cur.fetchall():
    d = dict(r)
    c = str(d.get('content', ''))[:80]
    p = str(d.get('payload_json', ''))[:80]
    print(f"  y={d['year']} t={d['term']} status={d.get('status')} content=[{c}] payload=[{p}]")

# 2. public.mode_payload_251 full schema
print('\n--- public.mode_payload_251 schema ---')
cur = conn.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='mode_payload_251' AND table_schema='public' ORDER BY ordinal_position")
for c in cur.fetchall():
    print(f"  {c['column_name']}: {c['data_type']}")

# 3. public.mode_payload_251 rows
print('\n--- public.mode_payload_251 rows ---')
cur = conn.execute("SELECT * FROM public.mode_payload_251 ORDER BY year DESC, term DESC LIMIT 5")
rows = cur.fetchall()
if rows:
    columns = list(rows[0].keys())
    print(f'Total columns: {columns}')
    for r in rows:
        d = dict(r)
        x = str(d.get('xiao', ''))
        c = str(d.get('content', ''))[:80]
        cd = str(d.get('code', ''))[:40]
        print(f"  y={d['year']} t={d['term']} web={d.get('web')} xiao=[{x}] code=[{cd}] content=[{c}]")
else:
    print('  NO ROWS')

# 4. created.mode_payload_251
print('\n--- created.mode_payload_251 schema ---')
try:
    cur = conn.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='mode_payload_251' AND table_schema='created' ORDER BY ordinal_position")
    for c in cur.fetchall():
        print(f"  {c['column_name']}: {c['data_type']}")
except Exception as e:
    print(f'Error: {e}')

print('\n--- created.mode_payload_251 rows ---')
try:
    cur = conn.execute("SELECT * FROM created.mode_payload_251 ORDER BY year DESC, term DESC LIMIT 5")
    rows = cur.fetchall()
    if rows:
        columns = list(rows[0].keys())
        print(f'Total columns: {columns}')
        for r in rows:
            d = dict(r)
            x = str(d.get('xiao', ''))
            c = str(d.get('content', ''))[:80]
            cd = str(d.get('code', ''))[:40]
            print(f"  y={d['year']} t={d['term']} web={d.get('web')} xiao=[{x}] code=[{cd}] content=[{c}]")
    else:
        print('  NO ROWS')
except Exception as e:
    print(f'Error: {e}')

# 5. Row counts
print('\n--- Row counts ---')
for schema in ('public', 'created'):
    cur = conn.execute(f"SELECT count(*) as cnt FROM {schema}.mode_payload_251")
    print(f'{schema}.mode_payload_251: {cur.fetchone()["cnt"]} rows')

# 6. Check for the user's expected row format - where does 'title' column exist?
print('\n--- Searching for title column ---')
cur = conn.execute("SELECT table_name FROM information_schema.columns WHERE column_name='title' AND table_schema='public' AND table_name LIKE '%251%'")
tables = [r['table_name'] for r in cur.fetchall()]
print(f'Tables with title column: {tables}')
