# 台湾百事通后端站点档案 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 通过版本迁移为 `twbst528` 建立 ID/web ID 均为 10 的独立后端预测档案，并仅公开其独立预测资料。

**Architecture:** 页面依赖清单是授权集合的唯一代码来源；migration 10 用该集合 upsert 蓝图和站点，再同步运行时模块行。已有 public site-page 按站点 `web_id` 过滤历史，测试固定验证 web 10 不会读取 web 9 数据。

**Tech Stack:** Python、PostgreSQL versioned migrations、现有 domains prediction/site service、pytest。

---

### Task 1: 声明首页的审核模块集合

**Files:**
- Modify: `backend/src/domains/prediction/site_page_dependencies.py`
- Modify: `backend/src/database/schema/prediction.py`
- Test: `backend/src/tests/unit/test_twbst528_page_dependencies.py`

- [x] 写失败测试，断言 `required_mode_ids_for_site_key('twbst528')` 仅包含首页 adapter 的 15 个机制对应的 mode ID。
- [x] 在依赖清单内为每个首页动态表建立一个 `SitePageDependency`，记录供应商入口、模块标题、机制 key 和单一 mode ID。
- [x] 在 bootstrap 档案常量和 profile seed 中加入 `twbst528`，使新数据库也具有同一蓝图集合。
- [x] 运行 `D:\python\python.exe -m pytest backend/src/tests/unit/test_twbst528_page_dependencies.py -q`，预期通过。

### Task 2: 创建可重复的站点 profile 迁移

**Files:**
- Modify: `backend/src/database/versioned_migrations.py`
- Test: `backend/src/tests/unit/test_versioned_migrations.py`

- [x] 写失败测试，构造 profile/site/module 表，调用新 migration 后断言 profile 为 `twbst528`，站点为 `id=10/web_id=10`，并且同步的模块模式集合匹配页面清单。
- [x] 实现 migration 10：upsert profile、upsert managed site、同步缺失模块；不导入或复制任何其他站点的预测行。
- [x] 将版本 10 加入 `MIGRATIONS` 并更新 `CURRENT_SCHEMA_VERSION`。
- [x] 运行 migration 测试子集，预期通过。

### Task 3: 纳入审计与资料隔离回归

**Files:**
- Modify: `backend/src/domains/prediction/site_module_audit.py`
- Modify: `backend/scripts/reconcile_site_prediction_modules.py`
- Test: `backend/src/tests/unit/test_site_prediction_module_audit.py`
- Test: `backend/src/tests/unit/test_site_prediction_modules_db_source.py`
- Test: `backend/src/tests/unit/test_public_module_history.py`

- [x] 写测试，验证 web 10 映射为 `twbst528`，审计和脚本默认范围包含 site 10。
- [x] 写公开历史隔离测试：同一 mode/table 中的 web 9 和 web 10 记录并存时，site 10 只序列化 web 10。
- [x] 更新审计映射与默认脚本 site list，不添加跨站 history 范围特例。
- [x] 运行相关 pytest 集合，预期通过。

### Task 4: 完整验证

**Files:**
- Modify: `backend/docs/API.md`（若现有站点配置文档需列出该新增站点）

- [x] 运行 `D:\python\python.exe -m pytest backend/src/tests/unit/test_twbst528_page_dependencies.py backend/src/tests/unit/test_versioned_migrations.py backend/src/tests/unit/test_site_prediction_module_audit.py backend/src/tests/unit/test_site_prediction_modules_db_source.py backend/src/tests/unit/test_public_module_history.py -q`。
- [x] 运行 `D:\python\python.exe -m pytest backend/src/tests/unit/test_site_context.py backend/src/tests/unit/test_api_contract_prediction_routes.py -q`。
- [x] 运行 `git diff --check`。
- [x] 在交接中说明：本地迁移代码已就绪；远端 PostgreSQL 必须由明确授权的部署操作执行 `python -m database.versioned_migrations --db-path "$DATABASE_URL"`，然后以 site 10 生成预测资料。
