# 号码集合类玩法「位置轮转 / 前两位不变」缺陷修复报告

- 仓库：`D:\pythonProject\outsource\Liuhecai`
- 范围：仅本地代码与测试；未 `git add/commit/push`，未连接任何服务器，未部署，未写入数据库。
- 工单现象：线上 `twsaimahui`（web_id 6）`10码中特`（mode 116，`038ma10.js` → `/api/kaijiang/getCode?num=10`）每期前两位恒为 `01.17`；`16码中特`（mode 9，`035ma16.js` → `num=16`）同样疑似。

---

## 一、根因复核（先复核，再采信）

### 1.1 复核结论：并行任务给出的「`unique_first_two` 轮转导致」对 mode 116/88 **不成立**

`enforce_prediction_diversity()` 里的 `unique_first_two` 策略确实写了「交换前两位 + 前四位左移一位」的旋转，但它对号码集合类玩法**从来没有执行过**，原因是解析层就过不去：

- 号码类玩法的 `content` 是普通逗号串 `"01,17,40,11,14,06,15,23,37,34"`（`predict.categories.number.format_24_numbers` = `",".join(labels)`）。
- `diversity.parse_array_content()` 只接受 `list` 或 `json.loads` 能解析的 JSON 数组串：`json.loads("01,17,40")` 抛 `ValueError` → 返回 `None`。
- 于是 `enforce_prediction_diversity()` 在 `if not items or len(items) < 2: return dict(row_data)` 处直接原样返回。
- 即使把 CSV 解析进去，`recent_first` / `recent_pairs` 也是从 `recent_rows` 的 content 构造的，而库里的 content 同样是 CSV → 两个集合恒为空 → `needs_repair` 永远为 `False`。

**实测证据（改动前的实测，只读）**：

```text
parse_array_content("01,17,40,11,14,06,15,23,37,34") = None
content_prefix_signature("01,17,40", width=2)         = None
enforce_prediction_diversity(116, {"content": "01,17,40,..."}, recent_rows=<库中真实 CSV 行>)
    → {'content': '01,17,40,11,14,06,15,23,37,34'}   # 与输入完全相同
```

用真实 `predict()` 输出跑一遍（term 88/89/90/91，mode 116/88），`content` 与 `after diversity` **逐字相同**，且没有 `_diversity_warning`：

```text
### mode=116 key=title_116 table=mode_payload_116
  term=88 raw content  = 01,17,40,11,14,06,15,23,37,34
          after diver. = 01,17,40,11,14,06,15,23,37,34   warn=None
### mode=88 key=title_88 table=mode_payload_88
  term=88 raw content  = 17,01,14,28,03,20,36
          after diver. = 17,01,14,28,03,20,36             warn=None
```

结论：`unique_first_two` 的轮转只对 **JSON 数组形态** 的 content 生效（如 `["家禽|牛,马,羊,鸡,狗,猪"]` 这类有序标签序列）。号码集合类玩法走的是「空转」。**真正把同一批号码钉在最前面的是生成侧的热度排序**（见 1.2）。

（顺带说明：即使轮转真的生效，它对集合语义也只是把同一批号码循环位移，位置 1 会在排名前 4 之间循环，仍然是「另一种固定」。所以本次修复选择对无序集合**停用**该轮转。）

### 1.2 真正的根因：`score_labels("hot")` 的热度窗口 + 「展示顺序 = 排名顺序」

链路：

1. `predict.common.predict()` → `score_labels(history, labels, label_count, lookback, "hot")`，其中
   `lookback = min(5, len(history))`、`recent = history[-5:]`；
   排序键 `key = (counts[label], random.random())`，`counts` 只统计这 5 条记录里出现过的特码号码。
2. `history` 来自 `predict_repository.load_recent_result_rows(conn, table_name, limit=10)`：取**共享源表**里最近 10 条 `res_code` 非空的行，**不按 web、也不按期号去重**，再按年/期升序返回。
   因此 `history[-5:]` 这 5 条常常只覆盖 1~2 个真实期号，同一个号码的 `counts` 被多站行重复累加。
3. 号码类玩法的 `content_formatter` 就是 `",".join(排名结果)`，于是**排名 = 展示顺序**，被重复累加的那 1~5 个号码固定占据前 1~5 位。

**实测（只读，`load_history` + `score_labels` 的输入窗口）**：

| mode | 玩法 | 源表每期行数（全表最大 / 近期） | `history[-5:]` 覆盖的真实期号 | 窗口内非零热度 | 由此得到的排名前缀 |
| ---: | --- | ---: | --- | --- | --- |
| 116 | 10码中特 | 12 / 4（web 1/5/6/7 各一行，同 `res_code`） | `122, 123, 123, 123, 123` | `01→4, 17→1` | **`01, 17, (其余随机)`** |
| 88 | 杀7码 | 6 / 2 | `121, 122, 122, 123, 123` | `01→2, 17→2, 14→1` | **`{01,17} 随机序, 14, …`** |
| 9 | 16码中特 | 6 / 8 | `127,128,129,130,131`（5 条 = 5 期，只有 1 行带开奖） | `39/36/23/22/08 各 1` | **`{39,36,23,22,08} 随机序, …`** |
| 34 | 24码 | 2 / 2 | `127…131` | 同上 | `{39,36,23,22,08} 随机序, …` |
| 65 | 码段12 | 2 / 2 | `127…131` | 同上 | `{39,36,23,22,08} 随机序, …` |

这一预测与线上落库数据**逐项吻合**（位置分布表见 1.3）：
- mode 116：`counts[01]=4` 独占第一 → 位置 1 = `01` 出现 38/40；`counts[17]=1` 次高 → 位置 2 = `17` 出现 25/40。
- mode 88：`counts[01]=counts[17]=2`（并列，`random.random()` 决定先后）→ 位置 1/2 只在 `{01,17}` 之间互换（19/18、17/19）；`counts[14]=1` → 位置 3 = `14` 出现 23/40。
- mode 9：5 个并列 `counts=1` → 位置 1~5 恒为 `{22,39,23,36,08}` 的随机排列 → 这正是工单说的「位置轮转」外观。

### 1.3 位置分布实测表（`created.mode_payload_*`，`web_id=6`，最近 40 期，只读）

| mode | 玩法 | 位置 1 分布 | 位置 2 分布 | 位置 3 分布 | 位置 1/2 组合 Top | ≥80% 出现率成员 | 位置 1 集中度 | 源表每期行数（近期） |
| ---: | --- | --- | --- | --- | --- | --- | ---: | ---: |
| 116 | 10码中特 | `01`×38, `37`×1, `34`×1（distinct=3） | `17`×25（distinct=12） | — | `(01,17)` 23/40 | `{01}` | 0.95 | 4 |
| 88 | 杀7码 | `01`×19, `17`×18, 其它 3 值×1（distinct=5） | `17`×19, `01`×17（distinct=6） | `14`×23（distinct=13） | `(01,17)` 12/40 + `(17,01)` 11/40 | `{01,17}` | 0.47 | 2 |
| 9 | 16码中特 | `22`×13, `39`×8, `23`×6, `36`×6, `08`×5 → **38/40 落在 5 个值**（distinct=7） | `39`×9, `23`×8, `22`×7, `08`×7, `36`×3 → **34/40 落在 5 个值**（distinct=11） | `08`×10, `23`×8, `39`×7, `36`×7 | `(22,39)` 4/40（前 5 位已被 5 值占住） | `{08,22,23,39}` | 0.33 | 8 |
| 34 | 24码 | 前 4 位被 `{08,22,23,39}` 占住 | — | — | — | `{08,22,23,39}` | 0.28 | 2 |
| 65 | 码段12 | 集中度 0.35 | — | — | — | — | 0.35 | 2 |

（全表扫描脚本对 `created.mode_payload_*` 中所有「content 可解析为纯 01-49 号码集合」的表逐个统计，只有上述 5 个 mode 命中该形态。）

### 1.4 轮转发生在哪一层

| 层 | 位置 | 行为 | 对 116/88/9 是否生效 |
| --- | --- | --- | --- |
| 生成层 | `predict/common.py::score_labels`（`strategy="hot"`）+ `predict_repository.load_recent_result_rows(limit=10)` | 按热度排序候选，`content` = 排名顺序 | **生效，这就是根因** |
| 展示/多样性层 | `prediction_generation/diversity.py::enforce_prediction_diversity`（`unique_first_two`） | 交换前两位 / 前四位左移一位 | **不生效（CSV 解析失败 + recent 签名恒空，空转）** |
| 持久化层 | `prediction_generation/service.py::_process_module` 第 ~2311 行 | 调 `enforce_prediction_diversity` 后写库 | 正常调用，但因为上一条等于没改 |

---

## 二、改动文件与关键 diff

### 2.1 `backend/src/prediction_generation/diversity.py`（主修复）

新增策略与白名单（+171 行）：

```python
UNORDERED_SET_DIVERSITY_POLICY = "unordered_set_display_order"

# 号码集合语义、且未登记受控未来期前缀契约的 mode
UNORDERED_NUMBER_SET_MODE_IDS: frozenset[int] = frozenset({9, 65, 88, 116})
```

- `resolve_diversity_policy()`：新增第 2 优先级 `if mode_id in UNORDERED_NUMBER_SET_MODE_IDS: return UNORDERED_SET_DIVERSITY_POLICY`（配置对象显式给出的 `diversity_policy` 仍然优先，保持既有优先级不变；生产 `PredictionConfig` 没有该字段，因此实际行为确定）。
- `enforce_prediction_diversity()`：新策略分支**不进入** `unique_first_two` 的交换/左移循环，改为

```python
if policy == UNORDERED_SET_DIVERSITY_POLICY:
    return unordered_number_set_display_order(mode_id, row_data, recent_rows=recent_rows)
```

- 新增 `number_set_members()` / `is_unordered_number_set_content()`（形态护栏：只有 `01`-`49` 两位数、长度 ≥2 才认定为号码集合；`["家禽|牛,马"]` 这类有序标签序列一律返回 `None`）；`_dump_number_set()`（list / JSON 数组串 / 逗号串三种落库形态原样回写）；`_number_set_shuffle_seed()`；`unordered_number_set_display_order()`；`_previous_number_set_order()`。
- 展示置换种子 = `sha256("unordered-number-set:{mode}:{year}:{term}:{web}:{成员}")`，用**局部** `random.Random(seed)`（不污染全局随机态，避免影响 `predict()` 里 `random.seed` 的语义）。含成员是为了在调用方漏传 `year/term/web` 时也不会退化成同一个固定置换。
- 置换后若与「最近一期成员完全相同」的展示顺序仍然一致，则整体错开一位 → 相邻期展示顺序必然不同（原来这里根本没生效的约束）。

**白名单取舍说明**：
- 覆盖 `9`（16码中特，工单点名）、`116`（10码中特，工单点名）、`88`（杀7码）、`65`（码段12）——这 4 个在 `domains/prediction/generation_rules.py::_RULE_BY_MODE_ID` 里都是 `blocked_pending_rule`，没有跨站前缀契约，且 `control_plan` 恒为 `None`，所以 `enforce_prediction_diversity` 对它们**全路径生效**（含台湾未来期）。
- **故意不含 `34`（24码）**：它登记了 `cross-site prefix: 3` 的跨站前缀契约（`backend/docs/prediction-module-rules.md` 第 17 行），也登记了 `481/485/493/494/77` 等号码类前缀契约。这些 mode 的受控未来期走 `control_plan is not None` 分支、本来就会跳过多样性处理，若强行改它们的展示顺序，会让「已预约的前缀签名」与「展示出来的前缀」脱钩。mode 34 的同样症状留给主线决策（报告第六节给了建议）。

### 2.2 `backend/src/domains/prediction/rule_documentation.py`

`prediction-module-rules.md` 是生成文档（`render_prediction_module_rules`）。新增 `_unordered_set_note()` / `_unordered_set_legend()`，把白名单 mode 的 `uniqueness` 列从
`cross-site prefix: N; adjacent: full ordered signature`
改为
`cross-site prefix: N; unordered number set: no positional rotation; adjacent: display order differs`，
并在文档头部生成一行图例：

```text
Unordered number-set modules (mode 9 / 65 / 88 / 116) never use positional rotation: their `content`
is a set of 01-49 numbers, so the display order is a per-issue permutation of the same members and the
adjacent-period contract is `display order differs` instead of `full ordered signature`.
```

### 2.3 `backend/docs/prediction-module-rules.md`

同步补上同一行图例（该文档当前列出的 mode 里没有 9/65/88/116，所以表格行不变，只新增图例）。

### 2.4 新增/补充测试

- 新增 `backend/src/tests/unit/test_prediction_number_set_display_order.py`（20 条）。
- `backend/src/tests/unit/test_prediction_rule_documentation.py` 新增 1 条（文档标注）。

### 2.5 未改动

- `predict/**`（生成算法、热度排序）、`prediction_generation/service.py`（调用点本来就正确）、`domains/prediction/generation_rules.py`（前缀宽度契约）。
- **任何已落库数据**：全部脚本只有 `SELECT`；没有 `INSERT/UPDATE/DELETE/DDL`，没有生成新期次，没有写 `prediction_generation_controls`。
- `docs/**`（含 `docs/prediction-display-standard.md`）——按工单要求只在第六节给出修改建议。

---

## 三、为什么判定语义不变（证据）

1. **实现层面**：置换只重排 `content` 里的成员，不增删任何号码。
   `test_membership_is_preserved_for_every_persisted_shape` 对 list / JSON 串 / CSV 三种形态断言「修复前后成员集合完全相同」；还断言 content 形态（list 仍是 list、JSON 串仍是 JSON 串、CSV 仍是 CSV）不变。
2. **判定函数层面**：号码类玩法的 `hit_checker` 是 `contains_hit`（010码等）与 `excludes_hit`（杀号类），两者都只做集合成员判定：
   - `contains_hit(outcome, labels)` = `outcome in labels`
   - `excludes_hit(outcome, labels)` = `outcome not in labels`
   `test_hit_semantics_identical_before_and_after_reorder` 对 `01`-`49` **全部 49 个特码取值**逐一双向比较修复前后的 `contains_hit` / `excludes_hit`，全部相等。
3. **回测解析层面**：`parse_number_content()` 用 `re.findall(r"\d{2}", item)` 提取全部号码，与顺序无关；历史命中率基线 `historical_content_hit_rate` 也不感知顺序。
4. **前台渲染层面**：`frontend/public/vendor/twsaimahui/static/js/038ma10.js` 第 20-31 行只做
   `ma = d.content.split(',')` → `ma[i].indexOf(code) !== -1`（高亮）→ `c1.join('.')`（展示），
   第 36 行 `开:${sx}${code}${zj?'准':'错'}` 的「准/错」完全由成员判断得出。`035ma16.js` 同构。
   即 **顺序 100% 是展示信息，不参与任何判定**。
5. **接口层面**：修复只作用于 `prediction_generation` 写库前的 `row_data["content"]`；`predict()` 的返回值（`prediction.labels` 的顺序）与即时 `/api/predict/{mechanism}` 响应结构均未改动。
6. **受控未来期层面**：有前缀契约的 mode（34/77/481/485/493/494…）走 `control_plan is not None` 分支，本来就不执行这段逻辑；白名单 4 个 mode 在 `generation_rules` 中是 `blocked_pending_rule`（`supported=False`），永远没有 control_plan，因此修复对它们**所有路径**生效且不触碰任何签名预约。
7. **「相邻期唯一性/多样性契约」未被削弱**：
   - `THREE_PERIOD_UNIQUE_MODE_IDS`（28/52/57/62/63/108/141/144/147/152/155/157/158）与 `CONTENT_DIVERSITY_EXEMPT_MODE_IDS`（197）完全未动，`enforce_three_period_uniqueness` 行为不变（相关 112 条定向测试全绿，见第四节）。
   - 对其他 mode，`unique_first_two` 的交换/左移行为逐字保留（`test_ordered_modes_still_use_unique_first_two_rotation`）。
   - 对白名单 mode，把「此前形同虚设的位置契约」替换为可验证的展示顺序契约：同期稳定 + 异期不同（`test_display_order_differs_from_the_previous_issue`、`test_display_order_is_stable_for_the_same_issue`）。

---

## 四、测试命令与前后数字

命令（工作目录 `backend/src`）：

```powershell
python -m pytest -q tests/ -k "diversity or three_period or generation"
python -m pytest -q
```

| 命令 | 修复前 | 修复后 | 说明 |
| --- | --- | --- | --- |
| 定向子集 | `1 failed, 111 passed, 4 skipped, 905 deselected`（3.91s） | `112 passed, 4 skipped, 905 deselected`（3.68s） | 修复前那次失败是我新增的 `test_resolve_diversity_policy_returns_unordered_set_policy`（把源码临时换回 HEAD 版本测的，测完已字节级还原并校验 SHA-256 一致）。`deselected` 数量一致（905），说明 `-k` 命中的测试集合除我新增的 1 条外没有变化。 |
| 全量 | `1 failed, 991 passed, 17 skipped`（144.92s，实测复核工单给出的基线） | `1 failed, 1015 passed, 17 skipped`（145.32s） | 唯一失败仍是既有失败 `tests/unit/test_ha_runtime_config_contract.py::test_nginx_exposes_exact_liveness_and_readiness_proxies`，与本次无关。 |

新增通过数核对：`1015 - 991 = 24` = 本次新增 21 条（`test_prediction_number_set_display_order.py` 20 条 + `test_prediction_rule_documentation.py` 1 条）+ 并行任务同时新增的 `tests/unit/test_legacy_frontend_compat_xiaoma2.py` 3 条（`git status` 可见该文件为未跟踪、非本次改动）。

**结论：没有引入新的失败。** 唯一失败与基线完全相同。

### 修复效果实测（同一批已落库内容，纯内存重放，未写库）

把 `created.mode_payload_*`（web_id=6）现有行按年/期升序喂给修复后的 `enforce_prediction_diversity`（`recent_rows` = 已处理行，模拟批量生成顺序）：

| mode | 行数 | 位置 1 distinct | 位置 1 Top | 位置 1/2 Top 组合 | 修复后位置 1 distinct | 修复后位置 1 Top |
| ---: | ---: | ---: | --- | --- | ---: | --- |
| 116 | 135 | 5 | `01`×131（97.0%） | `(01,17)` 68 | **43** | `01`×16（11.9%） |
| 88 | 135 | 7 | `01`×69 / `17`×61（96.3%） | `(01,17)` 66 + `(17,01)` 56 = 122 | **46** | `17`×21（15.6%） |
| 9 | 135 | 18 | `22`×37（27.4%） | `(22,08)` 12 | **44** | `08`×11（8.1%） |

真实生成链路抽样（调用真实 `predict()` + 修复后的多样性钩子，只读，未写库）：

```text
### mode=116 (10码)           raw content → after display order
  term=88  01,17,42,12,31,03,28,33,19,32  →  12,31,42,01,28,32,17,03,33,19
  term=89  01,17,05,43,22,42,27,46,44,41  →  46,44,22,05,42,27,41,43,01,17
  term=90  01,17,20,23,06,18,08,02,13,44  →  20,23,18,08,17,06,01,02,13,44
  term=91  01,17,46,06,42,04,33,19,34,22  →  04,33,42,22,17,34,46,19,06,01
### mode=9 (16码)
  term=88  23,39,22,36,08,...  →  11,08,20,48,01,35,22,49,23,06,39,45,18,34,25,36
  term=89  36,08,22,39,23,...  →  23,07,09,11,48,39,06,08,22,36,21,35,30,45,12,01
### mode=88 (杀7码)
  term=88  17,01,14,11,45,19,25  →  01,19,17,14,25,11,45
  term=89  17,01,14,21,48,07,27  →  48,17,27,21,01,07,14
```

（注意：`content` 的**成员集合**与 raw 完全一致，只有顺序变化 —— 这是判定语义等价的直接体现。）

---

## 五、后续新生成期次的预期变化

1. 只有**改动之后新生成并落库**的期次会带上新的展示顺序。
2. mode 9 / 65 / 88 / 116 的 `created.mode_payload_*.content` 仍然是同一批号码（生成算法、热度推荐、命中率控制、准确率控制全部不变），但：
   - 位置 1、位置 2 不再固定为 `01 / 17`，会随期号在整组号码里轮换（预期位置 1 的集中度从 95% 降到 ≈1/10）；
   - 相邻两期的展示顺序保证不同；
   - 同一期无论重算几次（重放 / 补跑），展示顺序稳定不变（种子含 `mode+年+期+站`），不会造成快照漂移；
   - 不同站点的同一期展示顺序不同（种子含 `web`），顺带降低跨站「看起来一模一样」的观感。
3. mode 9（16码）虽然 16 位里仍有 4~5 个号码出现率很高（这是热度推荐的**成员**问题，不是顺序问题），但前几位不再被那 5 个号码钉住。
4. 受控未来期（mode 34 等登记了 `cross-site prefix` 的号码类玩法）本次**行为不变**，见第六节的后续建议。

---

## 六、历史期次的处理说明 & 后续建议

### 6.1 历史期次

- **历史期仍然是旧的样子**：`created.mode_payload_*` 里已经落库的预测正文（含 116/88/9/65 的旧前缀）**一行都没有修改**，它们属于已落库数据；本次修复只改生成逻辑，从下一批新生成期次开始生效。
- 工单明确要求「不得修改已经落库的预测正文」，因此**没有**写任何数据迁移/回填脚本，也没有覆盖式重生成（`allow_overwrite` 路径未被调用）。
- 若主线希望历史展示也统一，需要单独立项（例如仅对「未开奖的未来期」做一次展示顺序重排，或新增迁移脚本），届时仍须保证成员不变、判定不变。

### 6.2 后续建议（本次未做，留给主线决策）

1. **mode 34（24码）等带跨站前缀契约的号码集合玩法**：同样有固定前缀症状（位置 1 集中度 0.28，前 4 位被 `{08,22,23,39}` 占住）。若要修复，需要同时把 `generation_rules` 的 `cross_site_prefix_width` 语义从「排名前 N 位」改成「展示前 N 位」，并重新审阅 `prediction_generation_controls` 已预约的 `prefix_signature`，属于契约变更，建议单独评审。
2. **热度窗口的跨站重复**（更深一层）：`load_recent_result_rows(limit=10)` 不带 `web` 过滤、也不按 `(year, term)` 去重，导致同一期号的多个站点行把同一个特码号码的 `counts` 重复累加（mode 116 实测 `01→4 / 17→1`）。这会让「热度」退化成「随机 + 一个固定赢家」，影响**所有**热度排序玩法（不只号码集合类）。建议按 `(year, term)` 去重后再统计（或按 web 过滤到本站），但这是**预测算法语义变更**，会影响候选成员分布与命中率基线，需要独立的回归评审，本次未纳入展示顺序修复范围内。
3. **`docs/prediction-display-standard.md` 的修改建议（本文件由主线维护，我未改动）**：
   - 第一节 S7「同一模块相邻 3 期以上展示值完全相同即为异常」对**多元素号码集合**几乎不触发——号码集合类玩法的异常形态是**位置固定**，建议补一条：号码集合类玩法应检查「位置 1/2 … 的取值集中度」与「≥80% 出现率成员数」，而不是整串相同。
   - 第六节「常见根因速查」现有的「全场都是同一个分组（全左肖/全阳肖…）」一行，处理办法写的是「把该 mode 加入 `THREE_PERIOD_UNIQUE_MODE_IDS`」——**这条对号码集合类不适用**（`display_token_for_row()` 对非托管 mode 返回 `None`，三期规则无法修复位置集中/成员集中问题；而且这里 position 不是语义）。建议新增一行：

     | 现象 | 常见根因 | 处理 |
     | --- | --- | --- |
     | 号码集合类玩法（10码中特 / 16码中特 / 杀7码）每期前几位固定、集合长期高度重复 | `score_labels("hot")` 的热度窗口只取源表最近 10 条带开奖行、不按期号去重（跨站重复行把同一号码的 counts 累加），热度最高的 1~5 个号码被固定在 content 最前面；而「展示顺序 = 排名顺序」，旧的 `unique_first_two` 轮转对纯逗号串是空转 | 把该 mode 加入 `prediction_generation.diversity.UNORDERED_NUMBER_SET_MODE_IDS`（停用位置轮转 + 按 `(mode,年,期,站)` 一次性置换展示顺序，成员不变）；**不要**只加 `THREE_PERIOD_UNIQUE_MODE_IDS` |

   - 第五节「R8」的提示也建议补一句：号码集合类玩法需额外核对位置分布，避免「成员集合正常但前几位被钉死」被漏判为正常。

---

## 七、交付物清单

| 文件 | 类型 | 说明 |
| --- | --- | --- |
| `backend/src/prediction_generation/diversity.py` | 修改 | 新增 `UNORDERED_SET_DIVERSITY_POLICY` / `UNORDERED_NUMBER_SET_MODE_IDS` / 号码集合解析与展示置换；`enforce_prediction_diversity` 对无序集合停用位置轮转 |
| `backend/src/domains/prediction/rule_documentation.py` | 修改 | 规则文档渲染器标注无序号码集合的展示顺序契约 |
| `backend/docs/prediction-module-rules.md` | 修改 | 同步新增图例一行 |
| `backend/src/tests/unit/test_prediction_number_set_display_order.py` | 新增 | 20 条：策略解析、形态护栏、位置不再固定、相邻期顺序不同、成员与判定等价、同期稳定、不误伤有序 mode |
| `backend/src/tests/unit/test_prediction_rule_documentation.py` | 修改 | +1 条：文档必须标注无序号码集合 |

未执行：`git add` / `git commit` / `git push`；任何服务器连接、部署、迁移、数据库写入。
