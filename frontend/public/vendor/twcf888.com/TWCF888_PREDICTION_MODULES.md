# TWCF888 Prediction Modules

## 2026-07-19 Page-Authorization Update

`public.site_prediction_modules(status=1)` is the runtime authorization source.
Its `twcf888` target set is derived only from prediction sources reachable from
the current frontend:

- `frontend/lib/twcf888-articles.ts` entries marked `live_backed`.
- `7637 特码单双`, which is the composite source `mode 28 + mode 57`.

The static vendor homepage's `MODULE_SECTION_META` is legacy display metadata.
It is not read by the current rendering/data-loading path and therefore does
not authorize its stale IDs. This prevents historical metadata from enabling
unused generation modules.

## Live-Backed Mode IDs

```text
2, 5, 12, 14, 15, 20, 26, 27, 28, 38, 41, 42, 43, 45, 47, 49, 50, 53, 54, 57, 66, 74, 88, 95, 98, 100, 103, 132, 143, 180, 198, 279, 470, 472, 473, 482, 483
```

Audit mirror (must remain identical to the list above):

```text
2, 5, 12, 14, 15, 20, 26, 27, 28, 38, 41, 42, 43, 45, 47, 49, 50, 53, 54, 57, 66, 74, 88, 95, 98, 100, 103, 132, 143, 180, 198, 279, 470, 472, 473, 482, 483
```

These IDs are the internal manifest and blueprint target. Reconciliation only
changes `site_prediction_modules.status` and timestamps; it never deletes
existing prediction history.

| Page source | mode_id | Status |
| --- | ---: | --- |
| `twcf888-articles.ts` live-backed articles | Direct IDs listed above except 28 and 57 | live_backed |
| `7637 特码单双` | `28 + 57` | live_backed composite |
| 广东5兄弟 | none | blocked_requires_backend_work |
| 官方图库 | none | snapshot_only |

## Snapshot-Only Items

| 模块 | 说明 |
| --- | --- |
| 官方图库 | 非预测模块，继续允许静态快照访问 |

## Blocked Items

| 模块 | 状态 |
| --- | --- |
| 广东5兄弟 | blocked_requires_backend_work |

规则:
- blocked 项不允许假映射到别的 mode_id.
- blocked 项首页与详情页都不能伪造 live 数据.
- 后续若要 live 化，必须先补后端机制或确认精确语义，再从 blocked 清单移入 required mode ids.
