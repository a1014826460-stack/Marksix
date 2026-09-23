# 十站开奖模块真实浏览器基线（2026-09-24）

工具：`frontend/test/live-site-draw-smoke.py`（只读访问公网生产站点，Playwright + 系统 Chrome；
本机未安装 Playwright 自带 chromium，脚本会回退到 `channel="chrome"`/`"msedge"`）。
另有 `frontend/test/live-draw-api-probe.py` 用于诊断"面板显示 --"时到底是接口问题还是面板问题
（它会在真实页面上下文里请求 `/api/next-draw-deadline`、`/api/latest-draw` 并打印面板的
`[local-kj]` 调试日志）。

指标定义：
- `DCLms`：导航到 `DOMContentLoaded`；
- `panelms`：开奖面板 iframe（`/vendor/shengshi8800/kj/local.html`）出现的时刻；
- `ballsms`：**面板首个号码球（`#m1`）真正显示出来的时刻**（这才是用户感知的"开奖出来了"）；
- 传输体积取 `performance.getEntriesByType('resource')` 的 `transferSize`。

## 基线（2026-09-24，图片压缩 + 面板并发/缓存 + nginx 边缘缓存 + 预测快照 P0 已上线）

| 站点 | DCLms | panelms | ballsms | 期号 | 号码数 | JS 错误 | 文档 KB | JS KB | 图片 KB |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| www.tw8800.com | 1655 | 2687 | 3641 | 266 | 7 | 1 | 11.0 | 146.1 | 0 |
| www.twcaibawang.com | **7452** | 7718 | **8108** | 266 | 7 | 0 | 10.2 | 155.9 | **1208.8** |
| www.twsaimahui.com | 1061 | 2108 | 2936 | 266 | 7 | 0 | 19.4 | 139.6 | 0 |
| www.twtongtian.com | 969 | 1984 | 2922 | 266 | 7 | 0 | 11.0 | 143.4 | 0 |
| www.twcf888.com | 952 | 1983 | 2812 | 266 | 7 | 0 | 28.6 | 143.4 | 0 |
| www.twssz.com | 921 | 2218 | 2468 | 266 | 7 | 0 | 27.1 | 139.6 | 0 |
| www.twbst528.com | 1094 | 2125 | 2406 | 266 | 7 | 0 | 17.9 | 139.6 | 0 |
| www.twjsz666.com | 1108 | 2389 | 2530 | 266 | 7 | 0 | 17.3 | 139.6 | 0 |
| www.twwanli.com | 1140 | 2702 | 2858 | 266 | 7 | 0 | 12.1 | 139.6 | 0 |
| www.twsyw.com | 1000 | 2297 | 2422 | 266 | 7 | 0 | 10.8 | 139.6 | 0 |

结论与解读：

1. **十站全部正常**：面板出现、7 个号码渲染、期号一致（266），除 tw8800 一个无关脚本错误外
   无 JS 报错 —— 说明已上线的面板改动（并发取数 + 5 秒缓存去重）没有破坏任何站点。
2. `ballsms` 比 `panelms` 多 200～1500 ms，正是面板自身的两次接口 + 渲染：
   已上线版本已是"并发取数"，剩余差异主要来自本机到站点的公网 RTT（经代理）。
3. **twcaibawang 仍是唯一的异常点**：DCL 7452 ms、图片 **1208.8 KB**。
   这两点对应的修复（SSR 两次聚合并发、内容图片 `loading="lazy"`）**已在本地提交但尚未部署**，
   部署后用同一工具复测即可看到下降。
4. 其余站点图片传输为 0 KB 是因为下面的图片都带 `loading="lazy"`，首屏不加载。

## 复测方法

```powershell
python frontend/test/live-site-draw-smoke.py                    # 十站
python frontend/test/live-site-draw-smoke.py twcaibawang twssz  # 指定站点
```

## 上线核查脚本（部署前后都用它）

`scripts/verify-perf-rollout.sh` 把本轮所有改动的验收标准固化成一条命令，只读、幂等，
每条打印 `PASS` / `PENDING`（未部署）/ `SKIP`（不在本节点服务范围）/ `FAIL`：

```bash
sh scripts/verify-perf-rollout.sh --role backend    # 中心节点：python-api 快照 + redis 代际键 + nginx 缓存
sh scripts/verify-perf-rollout.sh --role frontend   # 前端节点：Next 缓存标记 + twsaimahui bundle + 图片长缓存
```

要点：脚本先用 `nginx -T` 取出**本节点真正服务的域名**再逐条检查——非本节点域名会命中
default server 返回 `301`（169 字节重定向体），第一版因此误判了 5 站；现在归为 `SKIP`。

2026-09-24 试跑结果（当时 `ec17d6b`/`5b97953`/`59f1622` 尚未部署）：

| 节点 | PASS | PENDING | SKIP | FAIL |
| --- | --- | --- | --- | --- |
| 中心节点 | 14 | 1（代际计数键） | 8 | 0 |
| 前端节点 | 12 | 2（Next 缓存标记、twsaimahui bundle） | 7 | 0 |

即：**已上线的图片压缩、面板并发取数+缓存、nginx 边缘缓存、预测资料快照全部通过**，
未部署的三项被准确标记为 PENDING —— 部署后复跑应全部转为 PASS、PENDING 归零。

