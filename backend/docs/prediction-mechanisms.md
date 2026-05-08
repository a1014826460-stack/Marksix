# 预测机制文档

> 自动生成于 2026-05-08，从 `PREDICTION_CONFIGS` + `build_title_prediction_configs()` 提取。
> 后续维护时请同步更新本文档。

## 架构概述

```
predict()
  ├─ load_history(limit=10)   从 mode_payload_* 读取最近 10 条历史
  ├─ score_labels("balanced") 用 balanced 策略排序标签（偏离均值优先）
  ├─ historical_content()     计算原始历史 content 的命中率（基线参考）
  └─ content_formatter()      生成 content 返回给前端
```

不再进行策略回测和窗口遍历——彩票开奖随机，历史拟合不能预测未来。
预测的目的是为前端生成展示内容（生肖/号码/波色文本），不是追求统计命中率。

## 数据映射来源

所有生肖、波色、头、尾、大小、单双等结构化映射 **优先从 `public.fixed_data` 读取**。

### 三级查找策略（`build_pipe_value_map`）

1. `TABLE_FIXED_MAPPING_KEYS` 精确匹配（如 `mode_payload_12` → `头`）
2. 标签模糊匹配（扫描 `fixed_data` 所有 sign，找与标签集合匹配的 sign）
3. 回退到历史表 content 字段提取（仅在 `fixed_data` 无匹配时）

### 固定映射表

| 表名 | fixed_data sign | 示例 |
|---|---|---|
| mode_payload_12 | 头 | 0头: 01-09 |
| mode_payload_20 | 尾 | 0尾: 10,20,30,40 |
| mode_payload_26 | 琴棋书画 | (fixed_data 暂无，从历史推断) |
| mode_payload_28 | 单双 | 单: 奇数, 双: 偶数 |
| mode_payload_38 | 波色 | 红波: 01,02,07,08,... |
| mode_payload_53 | 五行肖 | 金肖: 鸡,猴 |
| mode_payload_54 | 尾 | 同上 |
| mode_payload_57 | 大小 | 大: 25-49, 小: 01-24 |
| mode_payload_58 | 波色单双 | 红单: 01,07,13,... |
| mode_payload_61 | 四季肖 | 春肖: 兔,虎,龙 |

## 硬编码配置清单

共 25 个手写配置 + 约 310 个动态生成配置。

### 生肖类
| key | title | modes_id | label_count | formatter |
|---|---|---|---|---|
| 3zxt | 3肖中特 | 69 | 3 | format_zodiac_csv |
| 6xzt | 6肖中特 | 46 | 6 | format_zodiac_csv |
| 9xzt | 9肖中特 | 49 | 9 | format_zodiac_csv |
| pt1xiao | 平特1肖 | 56 | 1 | format_zodiac_csv |
| pt2xiao | 平特2肖 | 43 | 2 | format_zodiac_csv |
| juesha3xiao | 绝杀3肖 | 42 | 3 | format_zodiac_csv |
| danshuang4xiao | 单双四肖 | 31 | 8 | format_xiao_pair |
| heibai3xiao | 黑白各3肖 | 45 | 6 | format_black_white |
| 7xiao7ma | 7肖7码 | 44 | 7 | format_zodiac_one_code |
| 4xiao8ma | 4肖8码 | 51 | 4 | format_zodiac_two_codes |
| 9xiao12ma | 9肖12码 | 60 | 9 | format_9x12 |

### 号码类
| key | title | modes_id | label_count | formatter |
|---|---|---|---|---|
| ma24 | 24码 | 34 | 24 | format_24_numbers |

### 分类选择类
| key | title | modes_id | label_count | formatter |
|---|---|---|---|---|
| 3tou | 3头中特 | 12 | 3 | format_head_groups |
| juesha1wei | 绝杀一尾 | 20 | 1 | format_tail_groups |
| pt1wei | 平特1尾 | 54 | 1 | format_tail_groups |
| danshuangtema | 单双中特 | 28 | 1 | format_parity_groups |
| daxiao | 大小中特 | 57 | 1 | format_size_groups |
| shuangbo | 双波中特 | 38 | 2 | format_wave_csv |
| jueshabanbo | 绝杀半波 | 58 | 1 | format_half_wave_groups |
| rcca | 肉菜草肖 | 3 | 2 | format_zodiac_groups |
| hllx | 红蓝绿肖 | 8 | 2 | format_zodiac_groups |
| siji3 | 四季生肖 | 61 | 3 | format_zodiac_groups |
| 3hang | 3行中特 | 53 | 3 | format_element_groups |
| qinqi | 琴棋书画 | 26 | 3 | format_qinqi_content |

### 文本历史映射类（is_text=1）
| key | title | modes_id | 文本来源 |
|---|---|---|---|
| dujiayoumo | 独家幽默 | 59 | text_history_mappings mode_id=59 → title+content |
| yijuzhenyan | 一句真言 | 50 | text_history_mappings → title+content+jiexi |
| sizixuanji | 四字玄机 | 52 | text_history_mappings → title+content+jiexi |
| yqjs | 欲钱解特 | 62 | text_history_mappings mode_id=62 → title |

### 动态生成配置（title_{modes_id}）
约 310 个，根据 `mode_payload_tables.title` 自动推断类型：
- 号码类：title 包含 "码"、"数"、"大小" → format_24_numbers
- 生肖类：title 包含 "肖中特"、"平特X肖"、"杀X肖" → format_zodiac_csv
- 尾数类：title 包含 "X尾"、"尾中特"、"必中X尾" → format_tail_groups
- 头数类：title 包含 "X头"、"头中特" → format_head_groups
- 波色类：title 包含 "波色" → format_wave_csv
- 结构化：content 包含 `|` → format_dynamic_pipe_groups
- 文本列：从 title/content/jiexi 字段提取生肖/尾数/波色
- 文本历史映射：title 含"真言/玄机/幽默/谜语/欲钱"等标记

## 性能参数

| 参数 | 值 | 说明 |
|---|---|---|
| 历史加载上限 | 10 条 | load_rows() LIMIT 10 |
| 预测策略 | hot（固定） | 近期高频标签优先，随开奖变化 |
| 回测 | 无 | 不遍历策略/窗口，直接生成 |
| 单次 predict() | ~0.06s | 相比优化前（2s）提升 33× |

## 维护指南

1. **新增预测机制**：在 `PREDICTION_CONFIGS` 中添加 `PredictionConfig` 条目，指定 key/title/labels/formatter
2. **新增 fixed_data 映射**：在 `public.fixed_data` 中 INSERT 对应 sign 的数据
3. **新增 mode_payload 表**：确保表在 `mode_payload_tables` 中注册，自动生成机制会自动识别
4. **文本类玩法**：确保 `text_history_mappings` 中有对应 `mode_id` 的数据
5. **修改映射关系**：直接修改 `fixed_data` 表中的 code 值，下次 predict() 调用时自动生效（无需重启）
