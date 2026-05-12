# domains/ 业务领域层：按业务领域组织 models、repository、service
#
# 职责：
# - models: 领域数据结构定义（dataclass）
# - repository: 数据库读写（SQL 集中在这里）
# - service: 业务逻辑编排（调用 repository + 外部服务）
