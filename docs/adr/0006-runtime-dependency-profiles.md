# Runtime Dependency Profiles

Production uses separate PostgreSQL write/read endpoints, managed Redis, S3-compatible object storage, three stateless Python API replicas, and HAProxy, while daily Windows development keeps one native PostgreSQL database, an in-process cache adapter, local filesystem assets, and one API process. Configuration falls back from `DATABASE_WRITE_URL` to the existing `DATABASE_URL`, from `DATABASE_READ_URL` to the write connection, and uses production-only validation to require Redis and object storage in formal runtime.

This split preserves the current fast local workflow without claiming that local substitutes validate distributed behavior. Redis atomic publication, read-replica routing, object storage, multi-instance operation, and failover must be covered by integration or pre-production tests before release.
