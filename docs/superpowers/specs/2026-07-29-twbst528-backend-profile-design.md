# 台湾百事通后端站点档案设计

## 目标

为 `twbst528` 建立独立、可重复部署的后端站点档案。该站固定使用
`managed_sites.id=10` 与 `managed_sites.web_id=10`；公开预测 API 只读取
`web_id=10` 的已授权预测资料，绝不回退或混用其他站点的资料。

## 范围

- 在页面依赖清单中登记首页已实现的 15 个简单表格模块及其已审计的
  mechanism/mode 映射。
- 通过 PostgreSQL 版本迁移幂等写入 `twbst528` 蓝图档案、站点记录及
  `site_prediction_modules` 授权行。
- 将该蓝图纳入 bootstrap 兼容的档案种子、模块审计和 reconciliation 工具。
- 验证前端同源接口 `/api/sites/twbst528/prediction-modules` 经
  `/api/public/site-page?site_id=10` 返回的模块只来自 `web_id=10`。

## 独立授权集合

首页当前适配器只渲染以下已审核的简单三列表和双波卡片，因此授权集合严格
限定为：

```text
50  一句真言             38  双波中特
44  7肖7码               43  平特2肖
58  绝杀半波             54  平特1尾
57  大小中特             51  4肖8码
56  平特1肖              5   天地生肖
47  4肖中特              470 平特3肖
472 绝杀1肖              28  单双中特
20  绝杀一尾
```

复杂供应商卡片尚未有独立 DOM renderer，因此不授权为首页动态模块；它们保留
静态页面后续逐个审计，不借用邻近模块数据。

## 数据隔离与生成

迁移只创建配置和授权，不复制其他站点的预测历史。后续管理员或 scheduler
对 site 10 的生成操作将以 `web_id=10` 写入 created/public payload 资料；公开
页固定以该站 `web_id` 过滤。若该站尚无生成资料，API 返回已授权模块及空
history，不返回任何其他站点记录。

## 迁移行为

新增 migration 10：

1. upsert `site_blueprint_profiles('twbst528')`，授权集合来自页面依赖清单；
2. upsert `managed_sites(id=10, web_id=10)`，名称为“台湾百事通”、域名为
   `www.twbst528.com`、默认彩种为台湾彩（3）、蓝图为 `twbst528`；
3. 调用既有 `sync_site_prediction_modules(conn, site_id=10)` 补齐缺失模块，
   不删除该站既有资料或手工状态；
4. 版本迁移账本和 PostgreSQL advisory lock 保持既有机制。

## 验收

- profile、站点 ID/web ID 及授权集合可由空 schema/已部署 schema 幂等得到。
- 站点 10 的授权模块与页面依赖清单完全一致，审计工具可报告它。
- API 使用 site 10 时不会读取 web 9 或其他 web 的 prediction rows。
- 生成服务对 site 10 的新记录使用 web/web_id 10。
- 迁移、授权、公开 API 隔离及生成相关回归测试通过。
