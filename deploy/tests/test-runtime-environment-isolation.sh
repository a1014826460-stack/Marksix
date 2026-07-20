#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
compose_file="$project_dir/docker-compose.yml"
deploy_file="$project_dir/deploy/deploy.sh"
verify_file="$project_dir/deploy/verify.sh"

grep -Fq 'LIUHECAI_RUNTIME_ENV: "production"' "$compose_file"
grep -Fq 'validate_production_environment' "$deploy_file"
grep -Fq 'Root .env must not define DATABASE_URL' "$deploy_file"
grep -Fq 'validate_production_environment' "$verify_file"
