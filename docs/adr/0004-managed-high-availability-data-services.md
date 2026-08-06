# Managed High-Availability Data Services

Liuhecai will keep its two existing application servers but move production PostgreSQL, Redis, and dynamic prediction assets to managed cross-availability-zone services. This provides automatic failover and independent storage failure domains without pretending that multiple processes on two physical servers form a safe quorum; Python API and scheduler candidates remain self-hosted and connect through stable managed endpoints.

The application servers continue to host the existing frontend Compatibility Layer and gain three stateless Python API replicas behind redundant HAProxy instances. PostgreSQL must provide synchronous high availability with a stable write endpoint and read endpoint, Redis must provide automatic failover, and object storage must provide S3-compatible lifecycle management.
