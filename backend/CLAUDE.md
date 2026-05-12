# 后端开发规范

## 1. 数据库

正式运行只使用 PostgreSQL。  
业务代码不得默认回退 SQLite。  
SQL 只能写在 repository、db、migration、created_store 中。  
不要在 routes、HTTP handler、前端页面中写 SQL。

## 2. 多站点

web_id 是站点业务 ID。  
managed_sites.id 是后台内部主键。  
managed_sites.web_id 对应旧资料表中的 web 字段。  
start_web_id/end_web_id 仅作为旧站抓取范围兼容字段。  
所有站点相关接口必须先解析 SiteContext。  
禁止硬编码 web=4。  
禁止通过 query/body 中的 web 参数跨站点读取或写入资料。

## 3. HTTP 路由

routes 只负责：
1. 解析 HTTP 参数
2. 鉴权
3. 调用 domain service
4. 返回 JSON

routes 不写复杂 SQL，不写预测生成细节。

## 4. 业务层

复杂业务逻辑放在 domains/*/service.py。  
数据库读写放在 domains/*/repository.py。  
公共数据结构放在 domains/*/models.py。

## 5. 预测

predict_engine 只做算法，不感知 HTTP、用户、站点权限。  
prediction generation 负责站点、期号、模块、created 表写入。  
历史回填可以使用 res_code。  
未来预测资料生成不能注入真实开奖结果。

## 6. 配置

业务代码通过配置服务读取配置，不直接到处读 config.yaml/env/system_config。  
敏感配置不要明文返回给前端。

## 7. 日志

生产代码禁止 print。  
关键日志必须尽量包含：
site_id、web_id、lottery_type_id、year、term、task_type、task_key、user_id。

## 8. 测试

修改以下内容必须补测试：
1. db schema
2. 多站点 SiteContext
3. prediction_generation
4. created_store
5. 路由分发
6. 配置管理
7. 日志查询
