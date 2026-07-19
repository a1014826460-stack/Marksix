# twsaimahui 预测模块部署清单

## 2026-07-19 页面依赖审计

`www.twsaimahui.com` 的模块授权只来自
`backend/src/domains/prediction/site_page_dependencies.py` 中当前
`index.html` 的非注释脚本。它覆盖每个可访问页面的精确 endpoint/`num`
映射；注释掉的脚本、孤立 JS 文件和无精确数据源的页面不会授权生成模块。

固定目标 mode IDs：

```text
3, 5, 8, 9, 10, 12, 15, 20, 22, 26, 27, 28, 30, 31, 38, 39, 41, 42, 45, 46, 47, 48, 49, 51, 53, 54, 56, 57, 58, 61, 63, 69, 88, 116, 123, 132, 141, 143, 144, 147, 149, 151, 152, 155, 157, 158, 159, 197, 251, 336, 470, 471, 472, 473
```

Audit mirror (must remain identical to the list above):

```text
3, 5, 8, 9, 10, 12, 15, 20, 22, 26, 27, 28, 30, 31, 38, 39, 41, 42, 45, 46, 47, 48, 49, 51, 53, 54, 56, 57, 58, 61, 63, 69, 88, 116, 123, 132, 141, 143, 144, 147, 149, 151, 152, 155, 157, 158, 159, 197, 251, 336, 470, 471, 472, 473
```

Important exact mappings:

| 页面脚本 | endpoint | mode_id |
| --- | --- | ---: |
| `035ma16.js` | `getCode?num=16` | 9 |
| `038ma10.js` | `getCode?num=10` | 116 |
| `067sanzipw.js` | `getPingte?num=3` | 470 |
| `072liangtou.js` | `getTou?num=2` | 471 |
| `057s1x.js` | `getShaXiao?num=1` | 472 |
| `058s2x.js` | `getShaXiao?num=2` | 473 |

## Blocked Page

| 页面脚本 | 原因 | 状态 |
| --- | --- | --- |
| `019liubuzhong.js` | 页面需要 `u6_code`，现有 `mode_payload_333` 不是同一 payload 语义 | blocked_data_source |

此页保持既有空响应形状；不得用其他 mode_id 伪造数据。同步命令只更新
`site_prediction_modules.status` 与时间戳，不删除预测历史，也不改变 API
响应字段或顺序。
