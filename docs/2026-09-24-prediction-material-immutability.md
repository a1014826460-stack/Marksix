# 预测资料不可变保证（自动流程不得改写或删除）

- 日期：2026-09-24
- 业务要求：**预测资料一旦生成，除管理员手动更改/删除外，任何自动流程都不得擅自改写或删除。**
- 适用范围：`created.mode_payload_*`（站点实际展示的预测正文）、`public.mode_payload_*`
  （资料源表）、预测结果字段 `res_code`/`res_sx`/`res_color`、预测模块授权表
  `site_prediction_modules`。

## 1. 结论

自动流程对预测资料只有两种合法动作：

1. **补缺失行**：`created.mode_payload_*` 中不存在 `type + year + term + web` 命中行时才插入；
2. **回填空的结果字段**：已开奖期的 `res_code`/`res_sx`/`res_color` 逐列填空，
   已有值（含管理员手工填写的值）一律不覆盖。

自动流程**没有任何 DELETE 语句**，也不触碰预测正文列（`content`/`title`/`image_url` 等）。

## 2. 写入/删除路径审计

### 2.1 管理员手动（唯一被允许的改写/删除来源）

| 入口 | 路由守卫 | 行为 |
| --- | --- | --- |
| `PUT/PATCH /api/admin/sites/{id}/mode-payload/{table}/{row}` | `require_admin` + 行归属校验 | 改写指定资料行（`source=public`/`created`） |
| `DELETE /api/admin/sites/{id}/mode-payload/{table}/{row}` | `require_admin` + 行归属校验 | 删除指定资料行 |
| `POST /api/admin/sites/{id}/prediction-modules/generate-all` | `require_admin` + `require_site_generation_access` | 批量重新生成，**显式** `allow_overwrite=True` |
| `DELETE /api/admin/sites/{id}/prediction-modules/bulk-delete` | `require_admin` + `require_site_generation_access` | 按期号范围批量删除生成行 |
| `POST /api/admin/backfill-predictions` | `require_admin` | 手动回填结果字段（允许整行覆盖，用于纠错） |
| `POST /api/admin/lottery-types/{id}/crawl-and-generate` | `require_admin` + 手动 job | 抓取后重新生成最近已开奖期，**显式** `allow_overwrite=True` |
| `POST /api/admin/normalize` | `require_admin` | 按 JSON 资料重建 `public.mode_payload_*`（DROP + CREATE） |
| `POST /api/admin/text-mappings` | `require_admin` | 重建 `text_history_mappings` |
| `PUT/PATCH/DELETE /api/admin/draws/{id}` | `require_admin` | 增删改开奖号码（影响命中判定显示） |
| `PUT/PATCH/DELETE /api/admin/sites/{id}/prediction-modules[/{module}]` | `require_admin` | 预测模块授权，不含正文 |

### 2.2 自动流程（只能补缺失行 / 回填空白结果字段）

| 入口 | 触发来源 | 覆盖保护 |
| --- | --- | --- |
| `_run_auto_prediction`（`crawler/scheduler.py`） | `trigger="daily_prediction"` | `_future_issue_has_predictions` 前置判断 + `allow_overwrite=False` |
| 近期缺口补跑 | `trigger="daily_prediction_recent_backfill"` | 只处理缺失模块 + `allow_overwrite=False` |
| 管理员手动每日预测任务 | `trigger="manual"` | `allow_overwrite=False` |
| `backfill_after_draw` 任务（开奖后延迟） | 调度器自动入队 | 只回填空白结果字段 + 缺口生成 `allow_overwrite=False` |
| `_backfill_draw_to_predictions` | 每次开奖后 | `fill_missing_created_prediction_result_fields`：逐列只填空值，逐表 SAVEPOINT 隔离 |

`created` 结果字段回填走 `backfill_repository.backfill_created_result_fields()`：逐表
`SAVEPOINT` + 缺列跳过 + 异常回滚，保证单表问题不会中止整次回填。

`crawler/` 目录下不存在针对 `mode_payload_*` / `created.*` 的 `UPDATE`（除结果字段回填）
或 `DELETE` 语句；开奖相关写入只落在 `lottery_draws` / `lottery_types`。

### 2.3 一次性迁移

`database/versioned_migrations.py::_import_twssz_static_prediction_history` 会把 twssz
供应商静态历史（`year=0`,`web=9`）导入 `created.mode_payload_*`。它受 `schema_migrations`
账本约束只执行一次，属于建库导入而非运行时自动改写。

## 3. 本轮加固（2026-09-24）

| 缺陷 | 加固前 | 加固后 |
| --- | --- | --- |
| 生成服务缺省覆盖 | `bulk_generate_site_predictions` 在缺少 `trigger` 时按 `admin_` 前缀推断，缺省 `allow_overwrite=True` | 缺省 `allow_overwrite=False`；覆盖必须显式传入 |
| 编排入口缺省覆盖 | `generate_prediction_batch(allow_overwrite=True)` | 缺省 `False` |
| 管理端批量生成依赖隐式缺省 | 前端不传 `allow_overwrite`，靠服务端缺省推断 | 管理端 `generate-all` 路由显式注入 `trigger="admin_generate_all"`、`allow_overwrite=True` |
| 抓取并生成依赖隐式缺省 | `crawler/collectors.py` 不传覆盖参数 | 显式声明 `trigger="admin_crawl_and_generate"`、`allow_overwrite=True`（管理台手动任务） |
| 自动结果回填会覆盖整行 | 任意一个结果字段为空即整行写入 `res_code`/`res_sx`/`res_color`，会覆盖管理员手工填写的列 | `fill_missing_created_prediction_result_fields` 逐列 `CASE WHEN 空值`，非空列保持原值 |
| 管理员全量改写后快照未失效 | `/api/admin/normalize`、`/api/admin/text-mappings`、删开奖号码后，预测快照最长 300 秒仍是旧资料 | 统一调用 `invalidate_all_lottery_types`（1/2/3 彩种粗粒度失效） |
| 结果字段回填被单表缺陷整次拖垮 | `created.mode_payload_273`/`335` 没有 `res_*` 列 → 该表 UPDATE 报错使 PostgreSQL 事务进入 aborted 状态 → 循环外的 `schema_table_exists` 探测抛 `current transaction is aborted` → 整次回填的更新全部丢失（线上 2026-09-23 13:47Z、14:40Z 各记录一次），已开奖期的结果字段长期为空 | 新增 `backfill_created_result_fields()`：逐表 `SAVEPOINT` + 缺 `res_*` 列直接跳过 + 异常 `ROLLBACK TO SAVEPOINT` 后继续；自动回填（`overwrite=False`）与管理台手动回填（`overwrite=True`）共用 |

自动结果回填的 SQL 形状（只填空值）：

```sql
UPDATE <created.mode_payload_x> SET
  res_code  = CASE WHEN res_code  IS NULL OR res_code  = '' OR REPLACE(res_code,  ',', '') = '' THEN ? ELSE res_code  END,
  res_sx    = CASE WHEN res_sx    IS NULL OR res_sx    = '' OR REPLACE(res_sx,    ',', '') = '' THEN ? ELSE res_sx    END,
  res_color = CASE WHEN res_color IS NULL OR res_color = '' OR REPLACE(res_color, ',', '') = '' THEN ? ELSE res_color END
WHERE type = ? AND year = ? AND term = ?
  AND (<res_code 为空> OR <res_sx 为空> OR <res_color 为空>)
```

管理员手动回填 `update_created_prediction_result_fields` 保持整行覆盖语义（纠错场景，例外条款）。

## 4. 防回归护栏

`backend/src/tests/unit/test_prediction_material_immutability.py`：

1. `generate_prediction_batch` / `bulk_generate_site_predictions` 缺省必须不覆盖；
2. 管理端 `generate-all` 路由必须显式授权覆盖；
3. 调度器每个自动生成调用点必须显式写 `allow_overwrite: False`（源码扫描，防止继承缺省值）；
4. 抓取并生成必须显式声明管理员来源；
5. 自动结果回填只填空白列，管理员手工填写的值不被覆盖，完整行零写入，其它期号/彩种不受影响；
6. 管理员手动回填仍可纠错；
7. `/api/admin/normalize` 与 `/api/admin/text-mappings` 必须失效 1/2/3 彩种快照；
8. 缺 `res_*` 列的表（线上 `mode_payload_273`/`335`）被跳过且不影响其它表；
9. 单表 SQL 失败被 SAVEPOINT 圈住，后续表仍完成回填；
10. 管理台手动回填（`overwrite=True`）仍可覆盖命中行。

验证命令：

```powershell
cd backend/src
python -m pytest tests/unit/test_prediction_material_immutability.py -q   # 13 passed
python -m pytest -q      # 最近一次：896 passed, 17 skipped, 1 pre-existing failure
```

## 5. 与预测快照的关系

`cache/prediction_snapshots.py` 只缓存**已经被公开端点返回过的 JSON**，版本键内容寻址，
指针 TTL 300 秒；它不写数据库、不生成资料。管理员改写/删除资料或开奖号码后，管理端路由
立即 bump 彩种代际，使该彩种全部快照失效，避免"管理员改了但站点最长 5 分钟仍显示旧资料"。
