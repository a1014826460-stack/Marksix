# 日志管理 & 配置信息管理 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在现有彩票后台管理系统中增量新增日志管理和配置信息管理两个后台板块。

**Architecture:** 严格遵循现有项目风格 — 后端在 `app.py` 单文件路由中新增 API，复用 `logger.py` 和 `runtime_config.py` 已有函数；前端在 `management-pages.tsx` 中新增 Client 组件，通过 Next.js 页面文件挂载。

**Tech Stack:** Python stdlib HTTP server, Next.js App Router, PostgreSQL/SQLite

---

## 文件结构

```
backend/src/
├── tables.py              [修改] 扩展 error_logs 列 + 新建 system_config_history 表
├── logger.py              [修改] 增强查询筛选 + 新增辅助查询函数
├── runtime_config.py      [修改] 增强 upsert 记录历史 + 新增配置 API 函数
├── app.py                 [修改] 新增日志和配置 API 路由
backend/
├── app/
│   ├── logs/page.tsx              [新增] 日志管理页面
│   ├── configs/page.tsx           [新增] 配置管理页面
├── components/admin/
│   ├── admin-shell.tsx            [修改] 添加菜单项
│   ├── management-pages.tsx       [修改] 新增 LogsPageClient / ConfigsPageClient
```

---

### Task 1: 扩展 `error_logs` 表字段

**Files:**
- Modify: `backend/src/tables.py`

- [ ] **Step 1: 在 `ensure_admin_tables()` 中添加 ensure_column 调用**

在 `ensure_admin_tables()` 函数中，`error_logs` 表创建之后（当前 logger.py 的 DatabaseLogHandler 中创建），在 `tables.py` 的 `ensure_admin_tables()` 末尾添加列扩展。由于 `error_logs` 表由 `logger.py:DatabaseLogHandler._ensure_table()` 创建，我们需要在 `tables.py` 中也确保表存在并扩展列。

在 `ensure_admin_tables()` 函数末尾（`_sync_modules(conn)` 之后）添加：

```python
# 确保 error_logs 表存在并扩展业务上下文字段
# 主表由 logger.py:DatabaseLogHandler 创建，这里做列兼容扩展
conn.execute(
    f"""
    CREATE TABLE IF NOT EXISTS error_logs (
        {conn.execute("SELECT 1").description}  -- placeholder, 实际由 logger.py 创建
    )
    """
)
# 扩展业务筛选维度列
ensure_column(conn, "error_logs", "site_id", "INTEGER")
ensure_column(conn, "error_logs", "web_id", "INTEGER")
ensure_column(conn, "error_logs", "lottery_type_id", "INTEGER")
ensure_column(conn, "error_logs", "year", "INTEGER")
ensure_column(conn, "error_logs", "term", "INTEGER")
ensure_column(conn, "error_logs", "task_key", "TEXT")
ensure_column(conn, "error_logs", "task_type", "TEXT")
ensure_column(conn, "error_logs", "request_path", "TEXT")
ensure_column(conn, "error_logs", "request_method", "TEXT")
```

但 `error_logs` 表是由 `logger.py:DatabaseLogHandler._ensure_table()` 创建的，它在每次 emit 时检查。我们需要确保在 `ensure_admin_tables()` 中先创建表（如果不存在），然后扩展列。实际做法：直接在这里用 `CREATE TABLE IF NOT EXISTS` 创建 error_logs 表（与 logger.py 中的定义一致），然后扩展列。

完整代码：

```python
# 确保 error_logs 表存在（与 logger.py:DatabaseLogHandler._ensure_table 定义一致）
# 表可能已被 logger.py 创建，这里确保列兼容并扩展业务上下文列
conn.execute(
    f"""
    CREATE TABLE IF NOT EXISTS error_logs (
        {pk_sql},
        created_at TEXT NOT NULL,
        level TEXT NOT NULL DEFAULT 'ERROR',
        logger_name TEXT NOT NULL DEFAULT '',
        module TEXT NOT NULL DEFAULT '',
        func_name TEXT NOT NULL DEFAULT '',
        file_path TEXT NOT NULL DEFAULT '',
        line_number INTEGER NOT NULL DEFAULT 0,
        message TEXT NOT NULL DEFAULT '',
        exc_type TEXT,
        exc_message TEXT,
        stack_trace TEXT,
        user_id TEXT,
        request_params TEXT,
        duration_ms REAL,
        extra_data TEXT
    )
    """
)
# 扩展业务筛选维度列（兼容已有数据库）
ensure_column(conn, "error_logs", "site_id", "INTEGER")
ensure_column(conn, "error_logs", "web_id", "INTEGER")
ensure_column(conn, "error_logs", "lottery_type_id", "INTEGER")
ensure_column(conn, "error_logs", "year", "INTEGER")
ensure_column(conn, "error_logs", "term", "INTEGER")
ensure_column(conn, "error_logs", "task_key", "TEXT")
ensure_column(conn, "error_logs", "task_type", "TEXT")
ensure_column(conn, "error_logs", "request_path", "TEXT")
ensure_column(conn, "error_logs", "request_method", "TEXT")
```

- [ ] **Step 2: 验证编译**

```powershell
python -m py_compile backend/src/tables.py
```

---

### Task 2: 创建 `system_config_history` 表

**Files:**
- Modify: `backend/src/tables.py`

- [ ] **Step 1: 在 `ensure_admin_tables()` 中添加建表语句**

在 `ensure_admin_tables()` 函数中，`ensure_system_config_table(conn)` 之后添加：

```python
# 配置变更历史表
conn.execute(
    f"""
    CREATE TABLE IF NOT EXISTS system_config_history (
        {pk_sql},
        config_key TEXT NOT NULL,
        old_value TEXT,
        new_value TEXT,
        changed_by TEXT,
        changed_at TEXT NOT NULL,
        change_reason TEXT,
        source TEXT NOT NULL DEFAULT 'admin'
    )
    """
)
```

- [ ] **Step 2: 验证编译**

```powershell
python -m py_compile backend/src/tables.py
```

---

### Task 3: 增强 `logger.py` — 扩展查询和辅助函数

**Files:**
- Modify: `backend/src/logger.py`

- [ ] **Step 1: 增强 `query_error_logs()` 函数签名和筛选逻辑**

修改 `query_error_logs()` 函数，替换现有筛选逻辑。在现有参数基础上添加新参数：

```python
def query_error_logs(
    db_path: str,
    *,
    page: int = 1,
    page_size: int = 30,
    level: str = "",
    module: str = "",
    keyword: str = "",
    date_from: str = "",
    date_to: str = "",
    user_id: str = "",
    site_id: str = "",
    web_id: str = "",
    lottery_type_id: str = "",
    year: str = "",
    term: str = "",
    task_type: str = "",
    task_key: str = "",
    path: str = "",
) -> dict[str, Any]:
    filters: list[str] = []
    params: list[Any] = []
    engine = ""

    with connect(db_path) as conn:
        engine = conn.engine
        if level:
            filters.append("level = ?")
            params.append(level.upper())
        if module:
            clause = "module ILIKE ?" if engine == "postgres" else "LOWER(module) LIKE LOWER(?)"
            filters.append(clause)
            params.append(f"%{module}%")
        if keyword:
            clause = (
                "(message ILIKE ? OR exc_message ILIKE ? OR stack_trace ILIKE ?)"
                if engine == "postgres"
                else "(LOWER(message) LIKE LOWER(?) OR LOWER(exc_message) LIKE LOWER(?) OR LOWER(stack_trace) LIKE LOWER(?))"
            )
            filters.append(clause)
            params.extend([f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"])
        if date_from:
            filters.append("created_at >= ?")
            params.append(date_from)
        if date_to:
            filters.append("created_at <= ?")
            params.append(date_to)
        # 新增筛选条件
        if user_id:
            filters.append("user_id = ?")
            params.append(user_id)
        if site_id:
            filters.append("site_id = ?")
            params.append(int(site_id))
        if web_id:
            filters.append("web_id = ?")
            params.append(int(web_id))
        if lottery_type_id:
            filters.append("lottery_type_id = ?")
            params.append(int(lottery_type_id))
        if year:
            filters.append("year = ?")
            params.append(int(year))
        if term:
            filters.append("term = ?")
            params.append(int(term))
        if task_type:
            clause = "task_type ILIKE ?" if engine == "postgres" else "LOWER(task_type) LIKE LOWER(?)"
            filters.append(clause)
            params.append(f"%{task_type}%")
        if task_key:
            clause = "task_key ILIKE ?" if engine == "postgres" else "LOWER(task_key) LIKE LOWER(?)"
            filters.append(clause)
            params.append(f"%{task_key}%")
        if path:
            clause = "request_path ILIKE ?" if engine == "postgres" else "LOWER(request_path) LIKE LOWER(?)"
            filters.append(clause)
            params.append(f"%{path}%")

        where = (" WHERE " + " AND ".join(filters)) if filters else ""
        offset = max(0, page - 1) * page_size
        total = int(conn.execute(f"SELECT COUNT(*) AS cnt FROM error_logs{where}", params).fetchone()["cnt"] or 0)
        rows = conn.execute(
            f"SELECT * FROM error_logs{where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params + [page_size, offset],
        ).fetchall()

    # 获取可用的 level 和 module 列表
    available_levels: list[str] = []
    available_modules: list[str] = []
    with connect(db_path) as conn:
        lv_rows = conn.execute("SELECT DISTINCT level FROM error_logs ORDER BY level").fetchall()
        available_levels = [str(r["level"]) for r in lv_rows]
        mod_rows = conn.execute("SELECT DISTINCT module FROM error_logs WHERE module != '' ORDER BY module").fetchall()
        available_modules = [str(r["module"]) for r in mod_rows]

    return {
        "items": [dict(row) for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size),
        "available_levels": available_levels,
        "available_modules": available_modules,
    }
```

注意：返回结构从 `"rows"` 改为 `"items"`，但为了向后兼容，保留 `"rows"` 的同时也加 `"items"`：

```python
    result = {
        "items": [dict(row) for row in rows],
        "rows": [dict(row) for row in rows],  # 向后兼容
        "total": total,
        ...
    }
```

- [ ] **Step 2: 新增 `get_log_modules()` 和 `get_log_levels()` 函数**

在 `logger.py` 末尾添加：

```python
def get_log_modules(db_path: str) -> list[str]:
    """返回 error_logs 表中所有已记录的模块名。"""
    with connect(db_path) as conn:
        rows = conn.execute(
            "SELECT DISTINCT module FROM error_logs WHERE module != '' ORDER BY module"
        ).fetchall()
        return [str(r["module"]) for r in rows]


def get_log_levels(db_path: str) -> list[str]:
    """返回 error_logs 表中所有已记录的日志等级。"""
    with connect(db_path) as conn:
        rows = conn.execute(
            "SELECT DISTINCT level FROM error_logs ORDER BY level"
        ).fetchall()
        return [str(r["level"]) for r in rows]
```

- [ ] **Step 3: 增强 `DatabaseLogHandler.emit()` — 记录更多上下文**

修改 `DatabaseLogHandler.emit()` 方法，在 INSERT 语句中添加新列：

```python
def emit(self, record: logging.LogRecord) -> None:
    try:
        with connect(self._db_path) as conn:
            self._ensure_table(conn)
            conn.execute(
                """
                INSERT INTO error_logs (
                    created_at, level, logger_name, module, func_name,
                    file_path, line_number, message, exc_type, exc_message,
                    stack_trace, user_id, request_params, duration_ms, extra_data,
                    site_id, web_id, lottery_type_id, year, term,
                    task_key, task_type, request_path, request_method
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    utc_now(),
                    record.levelname,
                    record.name,
                    str(getattr(record, "module", "") or ""),
                    record.funcName,
                    record.pathname,
                    record.lineno,
                    record.getMessage(),
                    type(record.exc_info[1]).__name__ if record.exc_info and record.exc_info[1] else None,
                    str(record.exc_info[1]) if record.exc_info and record.exc_info[1] else None,
                    "".join(traceback.format_exception(*record.exc_info)) if record.exc_info else None,
                    str(getattr(record, "user_id", "") or ""),
                    json.dumps(getattr(record, "req_params", None), ensure_ascii=False, default=str)
                    if getattr(record, "req_params", None) is not None
                    else None,
                    float(getattr(record, "duration_ms", 0)) if getattr(record, "duration_ms", None) is not None else None,
                    json.dumps(getattr(record, "result", None), ensure_ascii=False, default=str)
                    if getattr(record, "result", None) is not None
                    else None,
                    # 业务上下文字段
                    int(getattr(record, "site_id", 0)) if getattr(record, "site_id", None) is not None else None,
                    int(getattr(record, "web_id", 0)) if getattr(record, "web_id", None) is not None else None,
                    int(getattr(record, "lottery_type_id", 0)) if getattr(record, "lottery_type_id", None) is not None else None,
                    int(getattr(record, "year", 0)) if getattr(record, "year", None) is not None else None,
                    int(getattr(record, "term", 0)) if getattr(record, "term", None) is not None else None,
                    str(getattr(record, "task_key", "") or ""),
                    str(getattr(record, "task_type", "") or ""),
                    str(getattr(record, "request_path", "") or ""),
                    str(getattr(record, "request_method", "") or ""),
                ),
            )
    except Exception:
        pass
```

- [ ] **Step 4: 验证编译**

```powershell
python -m py_compile backend/src/logger.py
```

---

### Task 4: 增强 `runtime_config.py` — 变更历史和批量操作

**Files:**
- Modify: `backend/src/runtime_config.py`

- [ ] **Step 1: 修改 `upsert_system_config()` 记录变更历史**

在 `upsert_system_config()` 函数中，UPDATE/INSERT 执行后添加历史记录插入。修改后的函数在保存成功后添加：

```python
def upsert_system_config(
    db_path: str | Path,
    *,
    key: str,
    value: Any,
    value_type: str | None = None,
    description: str | None = None,
    is_secret: bool | None = None,
    changed_by: str = "",
    change_reason: str = "",
) -> dict[str, Any]:
    normalized_key = str(key or "").strip()
    if not normalized_key:
        raise ValueError("Configuration key cannot be empty.")

    default_meta = CONFIG_DEFAULTS.get(normalized_key, {})
    resolved_type = str(value_type or default_meta.get("value_type") or "string")

    with connect(db_path) as conn:
        ensure_system_config_table(conn)
        timestamp = utc_now()

        # 读取旧值用于历史记录
        old_row = conn.execute(
            f"SELECT value_text FROM {CONFIG_TABLE_NAME} WHERE key = ? LIMIT 1",
            (normalized_key,),
        ).fetchone()
        old_value = str(dict(old_row).get("value_text", "")) if old_row else None

        existing = conn.execute(
            f"SELECT id FROM {CONFIG_TABLE_NAME} WHERE key = ? LIMIT 1",
            (normalized_key,),
        ).fetchone()
        new_value_text = _serialize_value(value, resolved_type)

        if existing:
            conn.execute(
                f"""
                UPDATE {CONFIG_TABLE_NAME}
                SET value_text = ?, value_type = ?, description = ?, is_secret = ?, updated_at = ?
                WHERE key = ?
                """,
                (
                    new_value_text,
                    resolved_type,
                    str(description if description is not None else default_meta.get("description") or ""),
                    int(is_secret if is_secret is not None else default_meta.get("is_secret") or 0),
                    timestamp,
                    normalized_key,
                ),
            )
        else:
            conn.execute(
                f"""
                INSERT INTO {CONFIG_TABLE_NAME} (
                    key, value_text, value_type, description, is_secret, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    normalized_key,
                    new_value_text,
                    resolved_type,
                    str(description if description is not None else default_meta.get("description") or ""),
                    int(is_secret if is_secret is not None else default_meta.get("is_secret") or 0),
                    timestamp,
                    timestamp,
                ),
            )

        # 记录变更历史（仅当值确实发生变化时）
        if old_value is not None and old_value != new_value_text:
            conn.execute(
                """
                INSERT INTO system_config_history (
                    config_key, old_value, new_value, changed_by, changed_at, change_reason, source
                ) VALUES (?, ?, ?, ?, ?, ?, 'admin')
                """,
                (normalized_key, old_value, new_value_text, changed_by or "", timestamp, change_reason or ""),
            )
        elif old_value is None:
            # 新建配置也记录历史
            conn.execute(
                """
                INSERT INTO system_config_history (
                    config_key, old_value, new_value, changed_by, changed_at, change_reason, source
                ) VALUES (?, ?, ?, ?, ?, ?, 'admin')
                """,
                (normalized_key, "", new_value_text, changed_by or "", timestamp, change_reason or ""),
            )

        row = conn.execute(
            f"""
            SELECT key, value_text, value_type, description, is_secret, updated_at
            FROM {CONFIG_TABLE_NAME}
            WHERE key = ?
            LIMIT 1
            """,
            (normalized_key,),
        ).fetchone()
        return dict(row) if row else {}
```

- [ ] **Step 2: 新增配置相关辅助函数**

在 `runtime_config.py` 末尾添加：

```python
def get_config_groups() -> list[dict[str, Any]]:
    """返回配置分组列表，每个分组包含名称、前缀和说明。"""
    return [
        {"key": "lottery", "label": "彩种配置", "prefix": "draw.", "description": "各彩种开奖时间、数据源URL"},
        {"key": "scheduler", "label": "调度器配置", "prefix": "crawler.", "description": "自动开奖、抓取、预测延迟等调度参数"},
        {"key": "prediction", "label": "预测资料配置", "prefix": "prediction.", "description": "预测生成目标命中率、最大期数"},
        {"key": "site", "label": "站点配置", "prefix": "site.", "description": "站点默认URL、Token、请求参数"},
        {"key": "logging", "label": "日志配置", "prefix": "logging.", "description": "日志保留天数、轮转大小、清理间隔"},
        {"key": "auth", "label": "认证配置", "prefix": "auth.", "description": "Session过期时间、密码迭代次数"},
        {"key": "system", "label": "系统配置", "prefix": "admin.", "description": "管理员默认账号、显示名称"},
    ]


def get_config_effective(db_path: str | Path, key: str) -> dict[str, Any]:
    """返回单个配置的实际生效值及其来源信息。
    
    优先级：数据库 system_config > config.yaml 默认值。
    """
    default_meta = CONFIG_DEFAULTS.get(key, {})
    default_value = default_meta.get("value")
    default_type = str(default_meta.get("value_type") or "string")

    db_value = None
    source = "config.yaml"
    try:
        with connect(db_path) as conn:
            if conn.table_exists(CONFIG_TABLE_NAME):
                row = conn.execute(
                    f"SELECT value_text, value_type, updated_at FROM {CONFIG_TABLE_NAME} WHERE key = ? LIMIT 1",
                    (key,),
                ).fetchone()
                if row:
                    rd = dict(row)
                    db_value = _deserialize_value(
                        str(rd.get("value_text") or ""),
                        str(rd.get("value_type") or default_type),
                    )
                    source = "database"
    except Exception:
        pass

    effective_value = db_value if db_value is not None else default_value
    return {
        "key": key,
        "value": db_value,
        "default_value": default_value,
        "effective_value": effective_value,
        "value_type": default_type,
        "source": source,
        "description": str(default_meta.get("description", "")),
        "is_secret": bool(default_meta.get("is_secret", 0)),
        "updated_at": "",  # 从数据库读取时填充
    }


def list_configs_effective(
    db_path: str | Path,
    *,
    group: str = "",
    keyword: str = "",
    source: str = "",
) -> list[dict[str, Any]]:
    """返回所有配置的实际生效值列表，支持按分组、关键词、来源筛选。
    
    合并 database system_config 和 config.yaml 默认值，标注每个配置的来源。
    """
    groups = get_config_groups()
    group_map = {}
    for g in groups:
        for key in CONFIG_DEFAULTS:
            if key.startswith(g["prefix"]):
                group_map[key] = g["key"]

    results: list[dict[str, Any]] = []

    # 批量读取数据库中的配置
    db_values: dict[str, dict[str, Any]] = {}
    try:
        with connect(db_path) as conn:
            if conn.table_exists(CONFIG_TABLE_NAME):
                rows = conn.execute(
                    f"SELECT key, value_text, value_type, is_secret, description, updated_at FROM {CONFIG_TABLE_NAME} ORDER BY key"
                ).fetchall()
                for row in rows:
                    rd = dict(row)
                    db_values[str(rd["key"])] = rd
    except Exception:
        pass

    for key, meta in CONFIG_DEFAULTS.items():
        default_value = meta.get("value")
        default_type = str(meta.get("value_type") or "string")
        is_secret = bool(meta.get("is_secret", 0))
        desc = str(meta.get("description") or "")
        config_group = group_map.get(key, "system")

        # 分组筛选
        if group and config_group != group:
            continue

        # 关键词筛选
        if keyword and keyword.lower() not in key.lower() and keyword.lower() not in desc.lower():
            continue

        db_row = db_values.get(key)
        if db_row:
            db_value = _deserialize_value(
                str(db_row.get("value_text") or ""),
                str(db_row.get("value_type") or default_type),
            )
            effective_value = db_value
            config_source = "database"
            updated_at = str(db_row.get("updated_at", ""))
            # 如果数据库中有更详细的 description，使用数据库的
            if db_row.get("description"):
                desc = str(db_row["description"])
        else:
            db_value = None
            effective_value = default_value
            config_source = "config.yaml"
            updated_at = ""

        # 来源筛选
        if source and config_source != source:
            continue

        # 判断是否可编辑（敏感配置不可在页面上直接编辑值，但可以重新设置）
        editable = not is_secret

        # 判断是否需要重启（调度器和日志配置修改后通常需要重启生效）
        requires_restart = key.startswith(("logging.", "auth."))

        # 敏感配置的值不直接展示
        display_value = "***已配置***" if (is_secret and effective_value) else effective_value

        results.append({
            "key": key,
            "value": display_value,
            "raw_value": effective_value if not is_secret else None,
            "default_value": default_value,
            "effective_value": effective_value,
            "value_type": default_type,
            "group": config_group,
            "source": config_source,
            "description": desc,
            "editable": editable,
            "requires_restart": requires_restart,
            "sensitive": is_secret,
            "updated_at": updated_at,
        })

    return results


def reset_config(db_path: str | Path, key: str, changed_by: str = "") -> dict[str, Any]:
    """将指定配置恢复为 config.yaml 默认值。"""
    default_meta = CONFIG_DEFAULTS.get(key)
    if default_meta is None:
        raise ValueError(f"配置项 '{key}' 不存在默认值，无法恢复")

    with connect(db_path) as conn:
        ensure_system_config_table(conn)
        # 读取旧值
        old_row = conn.execute(
            f"SELECT value_text FROM {CONFIG_TABLE_NAME} WHERE key = ? LIMIT 1",
            (key,),
        ).fetchone()
        old_value = str(dict(old_row).get("value_text", "")) if old_row else ""

        default_value = default_meta.get("value")
        default_type = str(default_meta.get("value_type") or "string")
        default_desc = str(default_meta.get("description") or "")
        default_is_secret = int(default_meta.get("is_secret") or 0)
        timestamp = utc_now()
        new_value_text = _serialize_value(default_value, default_type)

        existing = conn.execute(
            f"SELECT id FROM {CONFIG_TABLE_NAME} WHERE key = ? LIMIT 1",
            (key,),
        ).fetchone()

        if existing:
            conn.execute(
                f"""
                UPDATE {CONFIG_TABLE_NAME}
                SET value_text = ?, value_type = ?, description = ?, is_secret = ?, updated_at = ?
                WHERE key = ?
                """,
                (new_value_text, default_type, default_desc, default_is_secret, timestamp, key),
            )

        # 记录变更历史
        conn.execute(
            """
            INSERT INTO system_config_history (
                config_key, old_value, new_value, changed_by, changed_at, change_reason, source
            ) VALUES (?, ?, ?, ?, ?, ?, 'admin')
            """,
            (key, old_value, new_value_text, changed_by or "", timestamp, "恢复默认值"),
        )

        row = conn.execute(
            f"SELECT key, value_text, value_type, description, is_secret, updated_at FROM {CONFIG_TABLE_NAME} WHERE key = ? LIMIT 1",
            (key,),
        ).fetchone()
        return dict(row) if row else {}


def batch_update_configs(
    db_path: str | Path,
    updates: list[dict[str, Any]],
    changed_by: str = "",
) -> dict[str, Any]:
    """批量更新配置。updates 格式: [{"key": "...", "value": ...}, ...]
    
    返回成功/失败统计。
    """
    success = 0
    failed: list[dict[str, str]] = []
    for item in updates:
        key = str(item.get("key", ""))
        value = item.get("value")
        value_type = str(item.get("value_type", "") or "")
        try:
            upsert_system_config(
                db_path,
                key=key,
                value=value,
                value_type=value_type if value_type else None,
                changed_by=changed_by,
            )
            success += 1
        except Exception as e:
            failed.append({"key": key, "error": str(e)})
    return {"success": success, "failed": len(failed), "failed_items": failed}


def get_config_history(
    db_path: str | Path,
    *,
    key: str = "",
    page: int = 1,
    page_size: int = 30,
) -> dict[str, Any]:
    """查询配置变更历史。"""
    filters: list[str] = []
    params: list[Any] = []
    if key:
        filters.append("config_key = ?")
        params.append(key)

    with connect(db_path) as conn:
        where = (" WHERE " + " AND ".join(filters)) if filters else ""
        offset = max(0, page - 1) * page_size
        total = int(
            conn.execute(
                f"SELECT COUNT(*) AS cnt FROM system_config_history{where}", params
            ).fetchone()["cnt"] or 0
        )
        rows = conn.execute(
            f"SELECT * FROM system_config_history{where} ORDER BY changed_at DESC LIMIT ? OFFSET ?",
            params + [page_size, offset],
        ).fetchall()

    return {
        "items": [dict(row) for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size),
    }


# ── 配置值校验 ─────────────────────────────────────────

def validate_config_value(key: str, value: Any, value_type: str) -> tuple[bool, str]:
    """校验配置值的类型和约束。返回 (is_valid, error_message)。"""
    if value_type == "int":
        try:
            v = int(value)
            # 特殊约束：部分配置必须是正整数
            positive_int_keys = {
                "crawler.auto_open_interval_seconds",
                "crawler.auto_crawl_interval_seconds",
                "crawler.auto_crawl_recent_minutes",
                "crawler.auto_prediction_delay_hours",
                "crawler.task_poll_interval_seconds",
                "crawler.task_lock_timeout_seconds",
                "crawler.task_retry_delay_seconds",
                "crawler.taiwan_precise_open_hour",
                "crawler.taiwan_precise_open_minute",
                "crawler.taiwan_max_retries",
                "crawler.http_timeout_seconds",
                "crawler.http_retry_count",
                "prediction.max_terms_per_year",
                "logging.max_file_size_mb",
                "logging.backup_count",
                "logging.error_retention_days",
                "logging.warn_retention_days",
                "logging.info_retention_days",
                "logging.max_total_log_size_mb",
                "logging.cleanup_interval_seconds",
                "logging.slow_call_warning_ms",
                "auth.session_ttl_seconds",
                "auth.password_iterations",
                "site.start_web_id",
                "site.end_web_id",
                "site.request_limit",
            }
            if key in positive_int_keys and v < 0:
                return False, f"'{key}' 不能为负数，当前值: {v}"
            return True, ""
        except (ValueError, TypeError):
            return False, f"'{key}' 需要整数类型，当前值: {value}"

    if value_type == "float":
        try:
            float(value)
            return True, ""
        except (ValueError, TypeError):
            return False, f"'{key}' 需要浮点数类型，当前值: {value}"

    if value_type == "bool":
        if isinstance(value, bool):
            return True, ""
        if str(value).strip().lower() in {"true", "false", "1", "0", "yes", "no", "on", "off"}:
            return True, ""
        return False, f"'{key}' 需要布尔类型 (true/false)，当前值: {value}"

    if value_type == "json":
        if isinstance(value, (dict, list)):
            return True, ""
        try:
            json.loads(str(value))
            return True, ""
        except (json.JSONDecodeError, TypeError):
            return False, f"'{key}' 需要合法 JSON 格式，当前值: {value}"

    if value_type == "time":
        import re
        if re.match(r"^\d{1,2}:\d{2}(:\d{2})?$", str(value).strip()):
            return True, ""
        return False, f"'{key}' 需要 HH:mm 或 HH:mm:ss 时间格式，当前值: {value}"

    # string 类型不做校验
    return True, ""
```

- [ ] **Step 3: 验证编译**

```powershell
python -m py_compile backend/src/runtime_config.py
```

---

### Task 5: 在 `app.py` 中添加新 API 路由

**Files:**
- Modify: `backend/src/app.py`

- [ ] **Step 1: 更新 import 语句**

在 `app.py` 顶部，更新从 `logger` 和 `runtime_config` 的导入：

```python
from logger import (
    export_error_logs, get_error_log_detail, get_log_modules, get_log_levels, get_log_stats,
    get_logger, init_logging, query_error_logs, trigger_cleanup,
)  # noqa: E402
from runtime_config import (
    batch_update_configs, get_config, get_config_effective, get_config_history,
    get_config_groups, list_configs_effective, list_system_configs,
    reset_config, upsert_system_config, validate_config_value,
)  # noqa: E402
```

- [ ] **Step 2: 替换现有日志查询 API（增强筛选参数）**

找到 `app.py:764-777` 的日志查询路由，替换为增强版本：

```python
if path == "/api/admin/logs" and method == "GET":
    qs = parse_qs(urlparse(self.path).query)
    result = query_error_logs(
        self.db_path,
        page=int(qs.get("page", ["1"])[0] or 1),
        page_size=min(int(qs.get("page_size", ["30"])[0] or 30), 200),
        level=qs.get("level", [""])[0],
        module=qs.get("module", [""])[0],
        keyword=qs.get("keyword", [""])[0],
        date_from=qs.get("date_from", [""])[0],
        date_to=qs.get("date_to", [""])[0],
        user_id=qs.get("user_id", [""])[0],
        site_id=qs.get("site_id", [""])[0],
        web_id=qs.get("web_id", [""])[0],
        lottery_type_id=qs.get("lottery_type_id", [""])[0],
        year=qs.get("year", [""])[0],
        term=qs.get("term", [""])[0],
        task_type=qs.get("task_type", [""])[0],
        task_key=qs.get("task_key", [""])[0],
        path=qs.get("path", [""])[0],
    )
    self.send_json(result)
    return
```

- [ ] **Step 3: 添加日志模块/等级 API**

在日志相关路由区域（现有 `/api/admin/logs/stats` 附近）添加：

```python
if path == "/api/admin/logs/modules" and method == "GET":
    self.send_json({"modules": get_log_modules(self.db_path)})
    return
if path == "/api/admin/logs/levels" and method == "GET":
    self.send_json({"levels": get_log_levels(self.db_path)})
    return
```

- [ ] **Step 4: 替换系统配置 API（增强功能）**

找到 `app.py:505-520` 的系统配置更新路由，增强为支持 `changed_by` 和校验：

```python
if method in {"PUT", "PATCH"} and path.startswith("/api/admin/system-config/"):
    config_key = path.split("/api/admin/system-config/", 1)[1].strip()
    body = self.read_json()
    value = body.get("value")
    value_type = str(body.get("value_type") or "")

    # 类型校验
    if value_type:
        is_valid, err_msg = validate_config_value(config_key, value, value_type)
        if not is_valid:
            self.send_error_json(HTTPStatus.BAD_REQUEST, err_msg)
            return

    user = auth_user_from_token(self.db_path, self.bearer_token())
    changed_by = user.get("username", "unknown") if user else "unknown"

    self.send_json(
        {
            "config": upsert_system_config(
                self.db_path,
                key=config_key,
                value=value,
                value_type=value_type or None,
                description=str(body.get("description") or "") or None,
                is_secret=body.get("is_secret"),
                changed_by=changed_by,
                change_reason=str(body.get("change_reason") or ""),
            )
        }
    )
    return
```

- [ ] **Step 5: 添加配置管理新 API 路由**

在系统配置 API 区域（现有 `/api/admin/system-config` GET 之后）添加：

```python
# 配置分组列表
if method == "GET" and path == "/api/admin/configs/groups":
    self.send_json({"groups": get_config_groups()})
    return

# 配置生效值列表（支持分组、关键词、来源筛选）
if method == "GET" and path == "/api/admin/configs/effective":
    qs = parse_qs(urlparse(self.path).query)
    group = qs.get("group", [""])[0]
    keyword = qs.get("keyword", [""])[0]
    source = qs.get("source", [""])[0]
    self.send_json({
        "configs": list_configs_effective(
            self.db_path,
            group=group,
            keyword=keyword,
            source=source,
        )
    })
    return

# 单个配置生效值
if method == "GET" and path.startswith("/api/admin/configs/effective/"):
    config_key = path.split("/api/admin/configs/effective/", 1)[1].strip()
    self.send_json(get_config_effective(self.db_path, config_key))
    return

# 批量更新配置
if method == "POST" and path == "/api/admin/configs/batch-update":
    body = self.read_json()
    updates = body.get("updates", [])
    if not isinstance(updates, list):
        self.send_error_json(HTTPStatus.BAD_REQUEST, "updates 必须是数组")
        return

    # 逐项校验
    for item in updates:
        key = str(item.get("key", ""))
        val = item.get("value")
        vt = str(item.get("value_type", ""))
        if vt:
            is_valid, err_msg = validate_config_value(key, val, vt)
            if not is_valid:
                self.send_error_json(HTTPStatus.BAD_REQUEST, f"配置 '{key}': {err_msg}")
                return

    user = auth_user_from_token(self.db_path, self.bearer_token())
    changed_by = user.get("username", "unknown") if user else "unknown"
    self.send_json(batch_update_configs(self.db_path, updates, changed_by=changed_by))
    return

# 恢复配置默认值
if method == "POST" and re.match(r"^/api/admin/configs/.+/reset$", path):
    config_key = path.rsplit("/", 2)[-2]
    user = auth_user_from_token(self.db_path, self.bearer_token())
    changed_by = user.get("username", "unknown") if user else "unknown"
    try:
        self.send_json({"config": reset_config(self.db_path, config_key, changed_by=changed_by)})
    except ValueError as e:
        self.send_error_json(HTTPStatus.NOT_FOUND, str(e))
    return

# 配置变更历史
if method == "GET" and path == "/api/admin/configs/history":
    qs = parse_qs(urlparse(self.path).query)
    config_key = qs.get("key", [""])[0]
    page = int(qs.get("page", ["1"])[0] or 1)
    page_size = min(int(qs.get("page_size", ["30"])[0] or 30), 200)
    self.send_json(get_config_history(self.db_path, key=config_key, page=page, page_size=page_size))
    return
```

注意：这些路由需要在 `dispatch()` 方法中正确的认证检查之后添加。`/api/admin/configs/*` 已经在 `/api/admin/` 认证检查之后，所以是安全的。

- [ ] **Step 6: 验证编译**

```powershell
python -m py_compile backend/src/app.py
```

---

### Task 6: 增强核心模块日志上下文

**Files:**
- Modify: `backend/src/crawler/crawler_service.py`

- [ ] **Step 1: 检查调度器日志上下文**

读取 `crawler_service.py`，在关键的爬虫和自动开奖调用处确保日志带有足够的上下文字段。主要检查点：

在 `_auto_open()` 函数中，记录开奖日志时通过 `extra` 参数传入 `site_id`、`lottery_type_id`、`year`、`term`、`task_type`。

在 `_auto_crawl()` 函数中类似处理。

由于 `crawler_service.py` 文件较大，只在关键入口点添加日志上下文，使用 `logging.LoggerAdapter` 或 `extra` 参数：

```python
import logging
_log = logging.getLogger("crawler")

# 在关键操作处：
_log.info(
    "Auto-open draw lottery_type_id=%s year=%s term=%s", 
    lottery_type_id, year, term,
    extra={
        "module": "crawler.auto_open",
        "task_type": "auto_open",
        "lottery_type_id": lottery_type_id,
        "year": year,
        "term": term,
    }
)
```

- [ ] **Step 2: 将明显 `print()` 改为 logger**

搜索 `crawler_service.py` 中的 `print()` 调用，改为使用 logger。

- [ ] **Step 3: 验证编译**

```powershell
python -m py_compile backend/src/crawler/crawler_service.py
```

---

### Task 7: 侧边栏 — 添加菜单项

**Files:**
- Modify: `backend/components/admin/admin-shell.tsx`

- [ ] **Step 1: 在 menuItems 数组中添加两个新项**

在 `admin-shell.tsx` 中，将 `FileText` 和 `Settings` 加入 lucide-react 导入，并在 `menuItems` 数组中添加：

```typescript
import {
  // ... 现有 imports
  FileText,
  Settings,
} from "lucide-react"

const menuItems = [
  { icon: LayoutDashboard, label: "控制台", href: "/" },
  { icon: Users, label: "管理员用户", href: "/users" },
  { icon: Trophy, label: "彩种管理", href: "/lottery-types" },
  { icon: Ticket, label: "开奖管理", href: "/draws" },
  { icon: Globe2, label: "站点管理", href: "/sites" },
  { icon: Hash, label: "静态数据管理", href: "/numbers" },
  { icon: BarChart3, label: "预测模块", href: "/prediction-modules" },
  { icon: FileText, label: "日志管理", href: "/logs" },
  { icon: Settings, label: "配置管理", href: "/configs" },
]
```

---

### Task 8: 前端 — 创建 `LogsPageClient` 组件

**Files:**
- Modify: `backend/components/admin/management-pages.tsx`

- [ ] **Step 1: 在 management-pages.tsx 中添加 LogsPageClient**

在文件末尾添加新的导出函数。需要导入 `FileDown` 图标：

```typescript
import { FileDown } from "lucide-react"
```

在文件末尾（`PredictionModulesPageClient` 之后）添加 `LogsPageClient`：

```typescript
type LogEntry = {
  id: number
  created_at: string
  level: string
  logger_name: string
  module: string
  func_name: string
  file_path: string
  line_number: number
  message: string
  exc_type?: string
  exc_message?: string
  stack_trace?: string
  user_id?: string
  site_id?: number
  web_id?: number
  lottery_type_id?: number
  year?: number
  term?: number
  task_key?: string
  task_type?: string
  request_path?: string
  request_method?: string
  duration_ms?: number
  request_params?: string
  extra_data?: string
}

function formatLogTime(ts: string) {
  if (!ts) return ""
  try {
    return ts.replace("T", " ").slice(0, 19)
  } catch { return ts }
}

function levelBadge(level: string) {
  const map: Record<string, string> = {
    ERROR: "bg-red-100 text-red-800 border-red-300",
    WARNING: "bg-yellow-100 text-yellow-800 border-yellow-300",
    INFO: "bg-blue-100 text-blue-800 border-blue-300",
    DEBUG: "bg-gray-100 text-gray-600 border-gray-300",
    CRITICAL: "bg-purple-100 text-purple-800 border-purple-300",
  }
  return map[level] || "bg-gray-100 text-gray-600 border-gray-300"
}

export function LogsPageClient() {
  const [items, setItems] = useState<LogEntry[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(30)
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState("")

  // 筛选状态
  const [level, setLevel] = useState("")
  const [module, setModule] = useState("")
  const [keyword, setKeyword] = useState("")
  const [dateFrom, setDateFrom] = useState("")
  const [dateTo, setDateTo] = useState("")
  const [userId, setUserId] = useState("")
  const [siteId, setSiteId] = useState("")
  const [lotteryTypeId, setLotteryTypeId] = useState("")

  // 可用选项
  const [availableLevels, setAvailableLevels] = useState<string[]>([])
  const [availableModules, setAvailableModules] = useState<string[]>([])

  // 详情弹窗
  const [detail, setDetail] = useState<LogEntry | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)

  async function load(p?: number) {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      params.set("page", String(p ?? page))
      params.set("page_size", String(pageSize))
      if (level) params.set("level", level)
      if (module) params.set("module", module)
      if (keyword) params.set("keyword", keyword)
      if (dateFrom) params.set("date_from", dateFrom)
      if (dateTo) params.set("date_to", dateTo)
      if (userId) params.set("user_id", userId)
      if (siteId) params.set("site_id", siteId)
      if (lotteryTypeId) params.set("lottery_type_id", lotteryTypeId)

      const data = await adminApi<{
        items: LogEntry[]
        total: number
        page: number
        page_size: number
        total_pages: number
        available_levels: string[]
        available_modules: string[]
      }>(`/admin/logs?${params}`)
      setItems(data.items)
      setTotal(data.total)
      if (p) setPage(p)
      setAvailableLevels(data.available_levels || [])
      setAvailableModules(data.available_modules || [])
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "加载失败")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load(1) }, [])

  async function showDetail(logId: number) {
    setDetailLoading(true)
    try {
      const data = await adminApi<LogEntry>(`/admin/logs/${logId}`)
      setDetail(data)
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "加载详情失败")
    } finally {
      setDetailLoading(false)
    }
  }

  async function handleExport() {
    try {
      const params = new URLSearchParams()
      if (level) params.set("level", level)
      if (module) params.set("module", module)
      if (keyword) params.set("keyword", keyword)
      if (dateFrom) params.set("date_from", dateFrom)
      if (dateTo) params.set("date_to", dateTo)

      const data = await adminApi<{ rows: LogEntry[] }>(`/admin/logs/export?${params}`)
      const csv = [
        ["时间", "等级", "模块", "消息", "错误类型", "错误消息", "文件", "行号", "用户ID", "站点ID", "彩种ID", "年份", "期数", "任务类型", "任务Key", "请求路径"].join(","),
        ...data.rows.map(r => [
          r.created_at, r.level, r.module, `"${(r.message || "").replace(/"/g, '""')}"`,
          r.exc_type || "", r.exc_message || "", r.file_path || "", r.line_number || "",
          r.user_id || "", r.site_id || "", r.lottery_type_id || "", r.year || "", r.term || "",
          r.task_type || "", r.task_key || "", r.request_path || ""
        ].join(","))
      ].join("\n")

      const blob = new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8" })
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = `logs_${new Date().toISOString().slice(0, 10)}.csv`
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "导出失败")
    }
  }

  function resetFilters() {
    setLevel("")
    setModule("")
    setKeyword("")
    setDateFrom("")
    setDateTo("")
    setUserId("")
    setSiteId("")
    setLotteryTypeId("")
    load(1)
  }

  const totalPages = Math.max(1, Math.ceil(total / pageSize))

  return (
    <AdminShell
      title="日志管理"
      description="查看系统错误日志、爬虫日志、调度任务日志、预测生成日志等信息。支持按等级、模块、时间筛选。"
      actions={
        <Button variant="outline" size="sm" onClick={handleExport}>
          <FileDown className="mr-1 h-4 w-4" />导出 CSV
        </Button>
      }
    >
      <AdminNotice message={message} />

      {/* 筛选区 */}
      <Card className="mb-4 p-4">
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
          <Field label="日志等级">
            <select value={level} onChange={(e) => setLevel(e.target.value)} className="h-9 w-full rounded-md border bg-background px-3 text-sm">
              <option value="">全部等级</option>
              {availableLevels.map(l => <option key={l} value={l}>{l}</option>)}
            </select>
          </Field>
          <Field label="模块">
            <select value={module} onChange={(e) => setModule(e.target.value)} className="h-9 w-full rounded-md border bg-background px-3 text-sm">
              <option value="">全部模块</option>
              {availableModules.map(m => <option key={m} value={m}>{m}</option>)}
            </select>
          </Field>
          <Field label="关键词">
            <Input value={keyword} onChange={(e) => setKeyword(e.target.value)} placeholder="搜索消息内容" />
          </Field>
          <Field label="开始时间">
            <Input type="datetime-local" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} />
          </Field>
          <Field label="结束时间">
            <Input type="datetime-local" value={dateTo} onChange={(e) => setDateTo(e.target.value)} />
          </Field>
          <Field label="用户ID">
            <Input value={userId} onChange={(e) => setUserId(e.target.value)} placeholder="用户ID" />
          </Field>
          <Field label="站点ID">
            <Input value={siteId} onChange={(e) => setSiteId(e.target.value)} placeholder="站点ID" />
          </Field>
          <Field label="彩种ID">
            <select value={lotteryTypeId} onChange={(e) => setLotteryTypeId(e.target.value)} className="h-9 w-full rounded-md border bg-background px-3 text-sm">
              <option value="">全部彩种</option>
              <option value="1">香港彩</option>
              <option value="2">澳门彩</option>
              <option value="3">台湾彩</option>
            </select>
          </Field>
        </div>
        <div className="mt-3 flex gap-2">
          <Button size="sm" onClick={() => load(1)}>查询</Button>
          <Button variant="outline" size="sm" onClick={resetFilters}>重置</Button>
        </div>
      </Card>

      {/* 日志表格 */}
      <Card className="overflow-auto p-0">
        {loading ? (
          <div className="px-4 py-8 text-center text-sm text-muted-foreground">加载中...</div>
        ) : items.length === 0 ? (
          <div className="px-4 py-8 text-center text-sm text-muted-foreground">暂无日志数据</div>
        ) : (
          <>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="min-w-[140px]">时间</TableHead>
                  <TableHead className="min-w-[60px]">等级</TableHead>
                  <TableHead className="min-w-[100px]">模块</TableHead>
                  <TableHead className="min-w-[200px]">消息</TableHead>
                  <TableHead className="min-w-[80px]">用户</TableHead>
                  <TableHead className="min-w-[60px]">站点</TableHead>
                  <TableHead className="min-w-[60px]">彩种</TableHead>
                  <TableHead className="min-w-[60px]">期号</TableHead>
                  <TableHead className="min-w-[80px]">耗时</TableHead>
                  <TableHead className="min-w-[80px]">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((row) => (
                  <TableRow key={row.id}>
                    <TableCell className="whitespace-nowrap text-xs">{formatLogTime(row.created_at)}</TableCell>
                    <TableCell>
                      <span className={`inline-block rounded border px-1.5 py-0.5 text-[10px] font-medium ${levelBadge(row.level)}`}>
                        {row.level}
                      </span>
                    </TableCell>
                    <TableCell className="text-xs">{row.module || "-"}</TableCell>
                    <TableCell className="max-w-[300px] truncate text-xs" title={row.message}>
                      {row.exc_type ? <span className="font-medium text-red-600 mr-1">[{row.exc_type}]</span> : null}
                      {row.message}
                    </TableCell>
                    <TableCell className="text-xs">{row.user_id || "-"}</TableCell>
                    <TableCell className="text-xs">{row.site_id || "-"}</TableCell>
                    <TableCell className="text-xs">
                      {row.lottery_type_id === 1 ? "香港" : row.lottery_type_id === 2 ? "澳门" : row.lottery_type_id === 3 ? "台湾" : row.lottery_type_id || "-"}
                    </TableCell>
                    <TableCell className="text-xs">{row.year && row.term ? `${row.year}-${String(row.term).padStart(3, "0")}` : "-"}</TableCell>
                    <TableCell className="text-xs">{row.duration_ms != null ? `${row.duration_ms}ms` : "-"}</TableCell>
                    <TableCell>
                      <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={() => showDetail(row.id)}>
                        详情
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>

            {/* 分页 */}
            <div className="flex items-center justify-between border-t px-4 py-2">
              <span className="text-xs text-muted-foreground">
                共 {total} 条，第 {page}/{totalPages} 页
              </span>
              <div className="flex items-center gap-2">
                <span className="text-xs text-muted-foreground">每页</span>
                <select value={pageSize} onChange={(e) => { setPageSize(Number(e.target.value)); load(1) }} className="h-7 rounded border bg-background px-1 text-xs">
                  {[20, 30, 50, 100].map((n) => <option key={n} value={n}>{n}</option>)}
                </select>
                <div className="flex gap-1 ml-2">
                  <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => load(page - 1)} className="h-7 text-xs">上一页</Button>
                  <Button variant="outline" size="sm" disabled={page >= totalPages} onClick={() => load(page + 1)} className="h-7 text-xs">下一页</Button>
                </div>
              </div>
            </div>
          </>
        )}
      </Card>

      {/* 详情弹窗 */}
      {detailLoading && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="rounded-lg bg-background p-6 shadow-xl">加载中...</div>
        </div>
      )}
      {detail && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={() => setDetail(null)}>
          <div className="max-h-[85vh] w-[800px] overflow-y-auto rounded-lg bg-background p-6 shadow-xl" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-base font-semibold">日志详情 #{detail.id}</h3>
              <Button variant="outline" size="sm" onClick={() => setDetail(null)}>关闭</Button>
            </div>
            <div className="space-y-3 text-sm">
              <div className="grid grid-cols-2 gap-2">
                <div><span className="text-muted-foreground">时间:</span> {formatLogTime(detail.created_at)}</div>
                <div><span className="text-muted-foreground">等级:</span> <span className={`inline-block rounded border px-1.5 py-0.5 text-[10px] font-medium ${levelBadge(detail.level)}`}>{detail.level}</span></div>
                <div><span className="text-muted-foreground">模块:</span> {detail.module || "-"}</div>
                <div><span className="text-muted-foreground">函数:</span> {detail.func_name || "-"}</div>
                <div><span className="text-muted-foreground">文件:</span> {detail.file_path || "-"}:{detail.line_number}</div>
                <div><span className="text-muted-foreground">耗时:</span> {detail.duration_ms != null ? `${detail.duration_ms}ms` : "-"}</div>
                {detail.user_id && <div><span className="text-muted-foreground">用户ID:</span> {detail.user_id}</div>}
                {detail.site_id && <div><span className="text-muted-foreground">站点ID:</span> {detail.site_id}</div>}
                {detail.lottery_type_id && <div><span className="text-muted-foreground">彩种ID:</span> {detail.lottery_type_id}</div>}
                {detail.year && <div><span className="text-muted-foreground">年份:</span> {detail.year}</div>}
                {detail.term && <div><span className="text-muted-foreground">期数:</span> {detail.term}</div>}
                {detail.task_type && <div><span className="text-muted-foreground">任务类型:</span> {detail.task_type}</div>}
                {detail.task_key && <div><span className="text-muted-foreground">任务Key:</span> {detail.task_key}</div>}
                {detail.request_path && <div><span className="text-muted-foreground">请求路径:</span> {detail.request_method || ""} {detail.request_path}</div>}
              </div>
              <div>
                <div className="text-muted-foreground mb-1 font-medium">消息:</div>
                <pre className="whitespace-pre-wrap rounded-md bg-muted p-3 text-xs max-h-[120px] overflow-y-auto">{detail.message}</pre>
              </div>
              {detail.exc_type && (
                <div>
                  <div className="text-muted-foreground mb-1 font-medium">异常类型:</div>
                  <div className="text-sm text-red-600">{detail.exc_type}: {detail.exc_message}</div>
                </div>
              )}
              {detail.stack_trace && (
                <div>
                  <div className="text-muted-foreground mb-1 font-medium">堆栈跟踪:</div>
                  <pre className="whitespace-pre-wrap rounded-md bg-muted p-3 text-xs max-h-[300px] overflow-y-auto font-mono">{detail.stack_trace}</pre>
                </div>
              )}
              {detail.request_params && (
                <div>
                  <div className="text-muted-foreground mb-1 font-medium">请求参数:</div>
                  <pre className="whitespace-pre-wrap rounded-md bg-muted p-3 text-xs max-h-[120px] overflow-y-auto font-mono">{detail.request_params}</pre>
                </div>
              )}
              {detail.extra_data && (
                <div>
                  <div className="text-muted-foreground mb-1 font-medium">额外数据:</div>
                  <pre className="whitespace-pre-wrap rounded-md bg-muted p-3 text-xs max-h-[120px] overflow-y-auto font-mono">{detail.extra_data}</pre>
                </div>
              )}
              <div>
                <div className="text-muted-foreground mb-1 font-medium">原始日志 JSON:</div>
                <pre className="whitespace-pre-wrap rounded-md bg-muted p-3 text-xs max-h-[200px] overflow-y-auto font-mono">{JSON.stringify(detail, null, 2)}</pre>
              </div>
            </div>
          </div>
        </div>
      )}
    </AdminShell>
  )
}
```

---

### Task 9: 前端 — 创建 `ConfigsPageClient` 组件

**Files:**
- Modify: `backend/components/admin/management-pages.tsx`

- [ ] **Step 1: 在 management-pages.tsx 中添加 ConfigsPageClient**

在 `LogsPageClient` 之后添加：

```typescript
type ConfigEntry = {
  key: string
  value: any
  raw_value?: any
  default_value: any
  effective_value: any
  value_type: string
  group: string
  source: string
  description: string
  editable: boolean
  requires_restart: boolean
  sensitive: boolean
  updated_at: string
}

type ConfigGroup = {
  key: string
  label: string
  prefix: string
  description: string
}

type ConfigHistoryEntry = {
  id: number
  config_key: string
  old_value: string
  new_value: string
  changed_by: string
  changed_at: string
  change_reason: string
}

function sourceBadge(source: string) {
  const map: Record<string, string> = {
    database: "bg-green-100 text-green-800",
    "config.yaml": "bg-blue-100 text-blue-800",
    environment: "bg-purple-100 text-purple-800",
    computed: "bg-gray-100 text-gray-600",
  }
  return map[source] || "bg-gray-100 text-gray-600"
}

export function ConfigsPageClient() {
  const [configs, setConfigs] = useState<ConfigEntry[]>([])
  const [groups, setGroups] = useState<ConfigGroup[]>([])
  const [activeGroup, setActiveGroup] = useState("")
  const [keyword, setKeyword] = useState("")
  const [sourceFilter, setSourceFilter] = useState("")
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState("")
  const [messageType, setMessageType] = useState<"success" | "error" | "info">("info")

  // 编辑弹窗
  const [editing, setEditing] = useState<ConfigEntry | null>(null)
  const [editValue, setEditValue] = useState("")
  const [editSaving, setEditSaving] = useState(false)
  const [changeReason, setChangeReason] = useState("")

  // 历史弹窗
  const [historyOpen, setHistoryOpen] = useState(false)
  const [historyKey, setHistoryKey] = useState("")
  const [historyItems, setHistoryItems] = useState<ConfigHistoryEntry[]>([])
  const [historyLoading, setHistoryLoading] = useState(false)
  const [historyPage, setHistoryPage] = useState(1)
  const [historyTotal, setHistoryTotal] = useState(0)

  // 批量编辑
  const [batchMode, setBatchMode] = useState(false)
  const [pendingChanges, setPendingChanges] = useState<Map<string, string>>(new Map())

  async function loadGroups() {
    try {
      const data = await adminApi<{ groups: ConfigGroup[] }>("/admin/configs/groups")
      setGroups(data.groups)
    } catch { /* ignore */ }
  }

  async function loadConfigs() {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (activeGroup) params.set("group", activeGroup)
      if (keyword) params.set("keyword", keyword)
      if (sourceFilter) params.set("source", sourceFilter)
      const data = await adminApi<{ configs: ConfigEntry[] }>(`/admin/configs/effective?${params}`)
      setConfigs(data.configs)
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "加载失败")
      setMessageType("error")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadGroups(); loadConfigs() }, [])
  useEffect(() => { loadConfigs() }, [activeGroup, sourceFilter])

  function showMessage(msg: string, type: "success" | "error" | "info" = "info") {
    setMessage(msg)
    setMessageType(type)
    setTimeout(() => setMessage(""), 5000)
  }

  function startEdit(config: ConfigEntry) {
    setEditing(config)
    if (config.sensitive) {
      setEditValue("")
    } else {
      setEditValue(config.raw_value !== undefined ? String(config.raw_value) : String(config.value ?? ""))
    }
    setChangeReason("")
  }

  async function saveEdit() {
    if (!editing) return
    setEditSaving(true)
    try {
      const body: any = { value: editValue, value_type: editing.value_type }
      if (editing.sensitive && !editValue) {
        showMessage("敏感配置不能设置为空值", "error")
        setEditSaving(false)
        return
      }
      if (editing.value_type === "bool") {
        body.value = editValue === "true"
      } else if (editing.value_type === "int") {
        body.value = parseInt(editValue) || 0
      } else if (editing.value_type === "float") {
        body.value = parseFloat(editValue) || 0
      } else if (editing.value_type === "json") {
        try {
          body.value = JSON.parse(editValue)
        } catch {
          showMessage("JSON 格式不合法", "error")
          setEditSaving(false)
          return
        }
      }
      if (changeReason) body.change_reason = changeReason

      await adminApi(`/admin/system-config/${encodeURIComponent(editing.key)}`, {
        method: "PUT",
        body: jsonBody(body),
      })
      showMessage(`配置 '${editing.key}' 已保存`, "success")
      setEditing(null)
      loadConfigs()
    } catch (e) {
      showMessage(e instanceof Error ? e.message : "保存失败", "error")
    } finally {
      setEditSaving(false)
    }
  }

  async function handleReset(key: string) {
    if (!confirm(`确定要将 '${key}' 恢复为默认值吗？`)) return
    try {
      await adminApi(`/admin/configs/${encodeURIComponent(key)}/reset`, { method: "POST" })
      showMessage(`配置 '${key}' 已恢复默认值`, "success")
      loadConfigs()
    } catch (e) {
      showMessage(e instanceof Error ? e.message : "恢复失败", "error")
    }
  }

  async function showHistory(key: string) {
    setHistoryKey(key)
    setHistoryOpen(true)
    setHistoryPage(1)
    await loadHistory(key, 1)
  }

  async function loadHistory(key: string, p: number) {
    setHistoryLoading(true)
    try {
      const data = await adminApi<{ items: ConfigHistoryEntry[]; total: number }>(
        `/admin/configs/history?key=${encodeURIComponent(key)}&page=${p}&page_size=20`
      )
      setHistoryItems(data.items)
      setHistoryTotal(data.total)
      setHistoryPage(p)
    } catch { /* ignore */ } finally { setHistoryLoading(false) }
  }

  function renderEditInput(config: ConfigEntry) {
    if (config.sensitive) {
      return (
        <div>
          <label className="mb-1 block text-xs font-medium">新值（敏感配置，当前值已脱敏）</label>
          <Input
            type="password"
            value={editValue}
            onChange={(e) => setEditValue(e.target.value)}
            placeholder="输入新值（留空则不修改）"
            className="h-9 text-sm"
          />
        </div>
      )
    }
    if (config.value_type === "bool") {
      return (
        <div>
          <label className="mb-1 block text-xs font-medium">当前值: {config.value ? "true" : "false"}</label>
          <select value={editValue} onChange={(e) => setEditValue(e.target.value)} className="h-9 w-full rounded-md border bg-background px-3 text-sm">
            <option value="true">true (启用)</option>
            <option value="false">false (停用)</option>
          </select>
        </div>
      )
    }
    if (config.value_type === "time") {
      return (
        <div>
          <label className="mb-1 block text-xs font-medium">当前值: {String(config.value ?? "")}</label>
          <Input
            value={editValue}
            onChange={(e) => setEditValue(e.target.value)}
            placeholder="HH:mm 如 21:30"
            className="h-9 text-sm"
          />
        </div>
      )
    }
    if (config.value_type === "json") {
      return (
        <div>
          <label className="mb-1 block text-xs font-medium">当前值: {String(config.value ?? "")}</label>
          <Textarea
            value={editValue}
            onChange={(e) => setEditValue(e.target.value)}
            placeholder='合法 JSON，如 {"key": "value"}'
            className="h-32 text-xs font-mono"
          />
        </div>
      )
    }
    if (config.value_type === "int" || config.value_type === "float") {
      return (
        <div>
          <label className="mb-1 block text-xs font-medium">当前值: {String(config.value ?? "")}</label>
          <Input
            type="number"
            value={editValue}
            onChange={(e) => setEditValue(e.target.value)}
            step={config.value_type === "float" ? "0.1" : "1"}
            className="h-9 text-sm"
          />
        </div>
      )
    }
    // string
    return (
      <div>
        <label className="mb-1 block text-xs font-medium">当前值: {String(config.value ?? "")}</label>
        <Input
          value={editValue}
          onChange={(e) => setEditValue(e.target.value)}
          className="h-9 text-sm"
        />
      </div>
    )
  }

  return (
    <AdminShell
      title="配置信息管理"
      description="统一查看和修改系统运行配置。修改敏感配置需谨慎，部分配置修改后需重启服务生效。"
    >
      <AdminNotice message={message} />

      {/* 分组 Tabs */}
      <div className="mb-4 flex flex-wrap gap-1.5 overflow-x-auto rounded-lg border bg-muted/20 p-2">
        <button
          onClick={() => setActiveGroup("")}
          className={`rounded-full px-3 py-1.5 text-sm font-medium transition-colors ${
            activeGroup === "" ? "bg-primary text-primary-foreground" : "bg-background text-foreground hover:bg-primary/10"
          }`}
        >
          全部
        </button>
        {groups.map((g) => (
          <button
            key={g.key}
            onClick={() => setActiveGroup(g.key)}
            className={`rounded-full px-3 py-1.5 text-sm font-medium transition-colors ${
              activeGroup === g.key ? "bg-primary text-primary-foreground" : "bg-background text-foreground hover:bg-primary/10"
            }`}
            title={g.description}
          >
            {g.label}
          </button>
        ))}
      </div>

      {/* 搜索 + 来源筛选 */}
      <div className="mb-4 flex gap-2">
        <Input
          placeholder="搜索配置项或说明..."
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") loadConfigs() }}
          className="max-w-xs"
        />
        <select
          value={sourceFilter}
          onChange={(e) => setSourceFilter(e.target.value)}
          className="h-9 rounded-md border bg-background px-3 text-sm"
        >
          <option value="">全部来源</option>
          <option value="database">数据库</option>
          <option value="config.yaml">配置文件</option>
        </select>
        <Button variant="outline" size="sm" onClick={loadConfigs}>搜索</Button>
        <div className="flex-1" />
        <Button variant="outline" size="sm" onClick={async () => {
          if (!confirm(`确定将所有显示筛选范围内的 ${configs.length} 条配置恢复为默认值吗？`)) return
          for (const c of configs) {
            if (c.source === "database" && c.editable) {
              await handleReset(c.key)
            }
          }
        }}>批量恢复默认</Button>
      </div>

      {/* 配置表格 */}
      <Card className="overflow-auto p-0">
        {loading ? (
          <div className="px-4 py-8 text-center text-sm text-muted-foreground">加载中...</div>
        ) : configs.length === 0 ? (
          <div className="px-4 py-8 text-center text-sm text-muted-foreground">暂无匹配配置</div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="min-w-[220px]">配置项</TableHead>
                <TableHead className="min-w-[120px]">当前值</TableHead>
                <TableHead className="min-w-[100px]">默认值</TableHead>
                <TableHead className="min-w-[60px]">类型</TableHead>
                <TableHead className="min-w-[70px]">来源</TableHead>
                <TableHead className="min-w-[160px]">说明</TableHead>
                <TableHead className="min-w-[60px]">可编辑</TableHead>
                <TableHead className="min-w-[60px]">需重启</TableHead>
                <TableHead className="min-w-[120px]">最后修改</TableHead>
                <TableHead className="min-w-[160px]">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {configs.map((config) => (
                <TableRow key={config.key}>
                  <TableCell className="text-xs font-medium font-mono">{config.key}</TableCell>
                  <TableCell className="max-w-[200px] truncate text-xs" title={String(config.value ?? "")}>
                    {config.sensitive ? "***已配置***" : String(config.value ?? "")}
                  </TableCell>
                  <TableCell className="max-w-[100px] truncate text-xs text-muted-foreground">
                    {config.sensitive ? "***" : String(config.default_value ?? "")}
                  </TableCell>
                  <TableCell className="text-xs">{config.value_type}</TableCell>
                  <TableCell>
                    <span className={`inline-block rounded border px-1.5 py-0.5 text-[10px] font-medium ${sourceBadge(config.source)}`}>
                      {config.source === "database" ? "数据库" : config.source === "config.yaml" ? "配置文件" : config.source}
                    </span>
                  </TableCell>
                  <TableCell className="max-w-[200px] truncate text-xs" title={config.description}>
                    {config.description}
                  </TableCell>
                  <TableCell className="text-xs">{config.editable ? "是" : "否"}</TableCell>
                  <TableCell className="text-xs">
                    {config.requires_restart ? <span className="text-amber-600 font-medium">是</span> : "否"}
                  </TableCell>
                  <TableCell className="whitespace-nowrap text-xs">
                    {config.updated_at ? config.updated_at.replace("T", " ").slice(0, 16) : "-"}
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-1">
                      {config.editable && (
                        <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={() => startEdit(config)}>
                          编辑
                        </Button>
                      )}
                      <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={() => showHistory(config.key)}>
                        历史
                      </Button>
                      {config.source === "database" && (
                        <Button variant="ghost" size="sm" className="h-7 text-xs text-amber-600" onClick={() => handleReset(config.key)}>
                          恢复默认
                        </Button>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </Card>

      {/* 编辑弹窗 */}
      {editing && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={() => setEditing(null)}>
          <div className="max-h-[80vh] w-[500px] overflow-y-auto rounded-lg bg-background p-6 shadow-xl" onClick={(e) => e.stopPropagation()}>
            <h3 className="mb-1 text-base font-semibold">编辑配置</h3>
            <div className="mb-3 text-xs text-muted-foreground space-y-1">
              <div>配置项: <code className="font-mono bg-muted px-1 rounded">{editing.key}</code></div>
              <div>类型: {editing.value_type} | 来源: {editing.source} | 需重启: {editing.requires_restart ? "是" : "否"}</div>
              <div>说明: {editing.description || "-"}</div>
            </div>
            {renderEditInput(editing)}
            <div className="mt-3">
              <label className="mb-1 block text-xs font-medium">修改原因（可选）</label>
              <Input value={changeReason} onChange={(e) => setChangeReason(e.target.value)} placeholder="例如：调整开奖时间" className="h-9 text-sm" />
            </div>
            {editing.requires_restart && (
              <div className="mt-3 rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-800">
                此配置修改后需要重启服务才能生效。
              </div>
            )}
            <div className="mt-4 flex justify-end gap-2">
              <Button variant="outline" size="sm" onClick={() => setEditing(null)}>取消</Button>
              <Button size="sm" onClick={saveEdit} disabled={editSaving}>
                {editSaving ? "保存中..." : "保存"}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* 变更历史弹窗 */}
      {historyOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={() => setHistoryOpen(false)}>
          <div className="max-h-[80vh] w-[700px] overflow-y-auto rounded-lg bg-background p-6 shadow-xl" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-base font-semibold">变更历史: <code className="font-mono text-sm bg-muted px-1 rounded">{historyKey}</code></h3>
              <Button variant="outline" size="sm" onClick={() => setHistoryOpen(false)}>关闭</Button>
            </div>
            {historyLoading ? (
              <div className="py-4 text-center text-sm text-muted-foreground">加载中...</div>
            ) : historyItems.length === 0 ? (
              <div className="py-4 text-center text-sm text-muted-foreground">暂无变更记录</div>
            ) : (
              <>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="min-w-[140px]">时间</TableHead>
                      <TableHead className="min-w-[200px]">旧值</TableHead>
                      <TableHead className="min-w-[200px]">新值</TableHead>
                      <TableHead className="min-w-[80px]">操作人</TableHead>
                      <TableHead className="min-w-[100px]">原因</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {historyItems.map((h) => (
                      <TableRow key={h.id}>
                        <TableCell className="whitespace-nowrap text-xs">{h.changed_at.replace("T", " ").slice(0, 19)}</TableCell>
                        <TableCell className="max-w-[180px] truncate text-xs font-mono" title={h.old_value}>{h.old_value || "(空)"}</TableCell>
                        <TableCell className="max-w-[180px] truncate text-xs font-mono" title={h.new_value}>{h.new_value}</TableCell>
                        <TableCell className="text-xs">{h.changed_by || "-"}</TableCell>
                        <TableCell className="text-xs">{h.change_reason || "-"}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
                {historyTotal > 20 && (
                  <div className="flex justify-center gap-2 mt-3">
                    <Button variant="outline" size="sm" disabled={historyPage <= 1} onClick={() => loadHistory(historyKey, historyPage - 1)}>上一页</Button>
                    <Button variant="outline" size="sm" disabled={historyPage * 20 >= historyTotal} onClick={() => loadHistory(historyKey, historyPage + 1)}>下一页</Button>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      )}
    </AdminShell>
  )
}
```

注意：需要在文件顶部导入额外的 lucide-react 图标。

---

### Task 10: 创建前端页面文件

**Files:**
- Create: `backend/app/logs/page.tsx`
- Create: `backend/app/configs/page.tsx`

- [ ] **Step 1: 创建 `backend/app/logs/page.tsx`**

```typescript
import { LogsPageClient } from "@/components/admin/management-pages"

export default function LogsPage() {
  return <LogsPageClient />
}
```

- [ ] **Step 2: 创建 `backend/app/configs/page.tsx`**

```typescript
import { ConfigsPageClient } from "@/components/admin/management-pages"

export default function ConfigsPage() {
  return <ConfigsPageClient />
}
```

---

### Task 11: 检查 `admin-shell.tsx` 中 `Textarea` 导入

**Files:**
- Modify: `backend/components/admin/management-pages.tsx`

`ConfigsPageClient` 使用了 `Textarea`，需要确认 management-pages.tsx 中已有导入。根据现有代码，`Textarea` 已经导入。

- [ ] **Step 1: 确认 management-pages.tsx 头部导入完整**

检查现有导入是否包含：
```typescript
import { FileDown, ... } from "lucide-react"
import { Textarea } from "@/components/ui/textarea"
```

如果 `FileDown` 未导入，需要添加到 lucide-react 导入行。

---

### Task 12: 文档更新

**Files:**
- Modify: `backend/README_CN.md`

- [ ] **Step 1: 在 README_CN.md 中添加日志管理和配置管理板块说明**

在 README_CN.md 末尾（"推荐部署实践"之前）添加新章节。

内容涵盖：
- 日志管理板块说明（页面路径、筛选能力、详情查看、导出）
- 配置管理板块说明（配置来源、分组、编辑、历史记录）
- 配置优先级说明
- 可修改配置项说明

---

### Task 13: 验证

**Files:** 无（只运行命令）

- [ ] **Step 1: Python 编译检查**

```powershell
python -m py_compile backend/src/tables.py
python -m py_compile backend/src/logger.py
python -m py_compile backend/src/runtime_config.py
python -m py_compile backend/src/app.py
```

- [ ] **Step 2: 前端 lint 和 build**

```powershell
cd backend
npm run lint
npm run build
```

- [ ] **Step 3: 功能验证 (手动)**

启动后端服务，访问：
- `http://127.0.0.1:8000/admin` → 侧边栏应有"日志管理"和"配置管理"
- `http://127.0.0.1:3002/logs` → 日志管理页面
- `http://127.0.0.1:3002/configs` → 配置管理页面
- 测试日志筛选、查看详情、导出
- 测试配置修改、恢复默认、查看历史
