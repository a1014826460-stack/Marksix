# shengshi8800 预测模块部署清单

## 2026-07-19 页面依赖审计

站点 4（`shengshi8800`，`web_id=4`）的模块授权仅来自
`backend/src/domains/prediction/site_page_dependencies.py` 中
`index.html` 的非注释预测脚本。每个条目记录实际调用的 endpoint、参数和
`mode_id`；不以历史数据库行或目录中未加载的静态文件扩大授权范围。

固定目标 mode IDs：

```text
2, 3, 8, 12, 20, 26, 28, 31, 34, 38, 42, 43, 45, 46, 48, 49, 50, 51, 52, 53, 54, 56, 57, 58, 59, 61, 62, 63, 65, 68, 108, 151, 197, 244, 246, 331
```

Audit mirror (must remain identical to the list above):

```text
2, 3, 8, 12, 20, 26, 28, 31, 34, 38, 42, 43, 45, 46, 48, 49, 50, 51, 52, 53, 54, 56, 57, 58, 59, 61, 62, 63, 65, 68, 108, 151, 197, 244, 246, 331
```

关键映射：

| 页面脚本 | endpoint | mode_id |
| --- | --- | ---: |
| `027ptw.js` | `getPingte?num=2` | 43 |
| `023sqzt.js` | `getSanqiXiao4new` | 197 |
| `tp5.js` | `getPmxjcz?num=6` | 331 |
| `019ma24.js` | `getCode?num=24` | 34 |
| `016teduan.js` | `getCodeDuan?num=12` | 65 |
| `011yqjt.js` | `getJuzi?num=yqmtm` | 68 |

`018shu3x.js` 与 `020ssx.js` 都是实际加载的脚本，均请求
`getShaXiao?num=3`，并归入同一 `mode_id=42`。去重仅发生在最终授权集，
不会省略页面依赖记录。

## 非授权资源

以下内容不代表预测资料来源，不能授权或重新启用任何模块：通用工具、jQuery、
`ajax_interceptor.js`、`handleSelect.js`、开奖/图库脚本 `kj.js`、`djck.js`、
没有预测 API 的 `tu1.js`，以及 HTML 注释中的 `/cj/*` 资源。历史上已经存在但
不在上方清单的 `64`、`66`、`67`、`69` 和 `470-478` 等行会由同步过程停用。

执行 reconciliation 时仅会更新 `site_prediction_modules.status` 和时间戳，绝不
删除预测历史或 `created` 行；禁用模块继续返回既有空数组/空历史包装，API 字段和
字段顺序保持不变。
