# Authoritative Draw Publication

An Opened Draw becomes publicly publishable only after its PostgreSQL transaction and a uniquely keyed Outbox event commit together. Redis and CDN snapshots are derived, versioned read models: consumers build a complete new snapshot and atomically switch the latest pointer, while prediction generation and other follow-up work remain asynchronous and cannot delay or roll back the authoritative draw.

Redis, CDN, Traffic Events, and Prediction Assets are not draw truth. Their failure must degrade to the most recent confirmed snapshot without exposing Future Issue results, creating a database retry storm, or allowing duplicate opening by bypassing the existing durable scheduler task and worker lease.
