import sys
sys.path.insert(0, 'backend/src')
from db import connect
from predict.mechanisms import build_title_prediction_configs
from predict.common import predict

DB = 'postgresql://postgres:2225427@localhost:5432/liuhecai'

configs = build_title_prediction_configs(DB)
cfg = configs['title_251']
print(f'Config: key={cfg.key} label_count={cfg.label_count} table={cfg.default_table}')

# Run predict() for a real draw
conn = connect(DB)
result = predict(
    config=cfg,
    res_code='06,29,42,13,27,31,36',
    source_table='mode_payload_251',
    db_path=DB,
    target_hit_rate=0.5,
    conn=conn,
)

content = result['prediction']['content']
print(f'\npredict() output keys: {list(content.keys())}')
print(f'  title: [{content.get("title", "")}]')
print(f'  xiao:  [{content.get("xiao", "")}]')

if content.get('xiao'):
    print('\nSUCCESS: xiao is non-empty!')
else:
    print('\nFAIL: xiao is still empty')
