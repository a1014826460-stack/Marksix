# 台湾万利网接入 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将供应商模板接入为 web 12 的台湾万利网，并使用同源 API 在既有 DOM 内渲染三种彩票。

**Architecture:** 原模板放在 `public/vendor/twwanli`；manifest 注册身份，站点 adapter 声明既有节点。浏览器 adapter 只更新预声明叶节点并按彩票隔离缓存；后端 profile 授权经过文档审查的成熟模块。

**Tech Stack:** Next.js、TypeScript、浏览器 JavaScript、Python、Playwright、Node contract tests。

---

### Task 1: 站点资产和身份
- [ ] 复制模板至 `frontend/public/vendor/twwanli/`，运行 `pnpm site:scaffold --site-key twwanli`。
- [ ] 完成 manifest、site adapter、配置与共享友情链接挂载，运行 `pnpm site:sync-manifests` 和 `pnpm site:validate --site-key twwanli`。

### Task 2: 浏览器合同先行
- [ ] 新增 `frontend/test/twwanli-adapter-contract.mjs` 和 `frontend/test/twwanli-live-mapping-contract.py`，覆盖身份、三彩请求、叶节点、哨兵清理、三张属性图。
- [ ] 在 adapter 尚未实现时运行 Node contract，预期因缺文件失败。

### Task 3: DOM 适配器
- [ ] 在入口预声明动态期号、预测和结果叶节点；保留供应商布局与标签。
- [ ] 实现命名 formatter/renderer、去重、空态、特别号结果、命中重置和跨 frame tab；运行 twwanli contracts 由红转绿。

### Task 4: 后端授权
- [ ] 在 `site_page_dependencies.py` 列出首页 live module 和 mode id。
- [ ] 在 `site_module_blueprints.py` 与 `versioned_migrations.py` 新增 web 12 profile、managed site 和 module sync；添加隔离 SQLite 单测。

### Task 5: 完整验证
- [ ] 运行 manifest validation、twwanli Node/Python contracts、adapter registry、data client、baseline、`tsc` 与生产构建。
- [ ] 若本地数据库有 web 12 数据，检查三种彩票同源 API 和 distinct issues；无数据只报告缺口，绝不借用其他 web 行。
