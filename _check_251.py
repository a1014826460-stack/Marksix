import sys
sys.path.insert(0, 'backend/src')
from db import connect

try:
    conn = connect('postgresql://postgres:postgres@localhost:5432/liuhecai')
    for schema in ('public', 'created'):
        cur = conn.execute(
            f"SELECT column_name, data_type FROM information_schema.columns "
            f"WHERE table_name = 'mode_payload_251' AND table_schema = '{schema}' "
            f"ORDER BY ordinal_position"
        )
        cols = cur.fetchall()
        if cols:
            print(f'{schema}.mode_payload_251 columns:')
            for c in cols:
                print(f'  {c["column_name"]}: {c["data_type"]}')
            cur2 = conn.execute(
                f"SELECT year, term, xiao, code, "
                f"substring(content,1,80) as content_sample "
                f"FROM {schema}.mode_payload_251 "
                f"ORDER BY year DESC, term DESC LIMIT 3"
            )
            rows = cur2.fetchall()
            print(f'  Rows ({len(rows)}):')
            for r in rows:
                xiao_val = str(r.get('xiao', 'N/A'))
                code_val = str(r.get('code', 'N/A'))
                print(f'    y={r["year"]} t={r["term"]} xiao=[{xiao_val}] code=[{code_val}]')
        else:
            print(f'{schema}.mode_payload_251: DOES NOT EXIST')
except Exception as e:
    print(f'Error: {e}')
