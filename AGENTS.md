# Deployment Authorization

- Do not connect to any server, run `git pull` or `git push` remotely, transfer files, build or restart remote services, run migrations, inspect remote state, or otherwise perform remote operations unless the user explicitly authorizes the server and the requested operation in the current message.
- A previous deployment authorization does not authorize later server access. Ask for a new explicit instruction before every separate remote operation.

# 并发会话协作约定（2026-09-28）

同一个工作区可能同时有多个会话/代理在改代码（已实际发生：出现过来自其它会话的提交
`ae0901b`、`6f294f7`，以及 178 行未提交的 `frontend/public/vendor/twbst528/site-data-adapter.js` 改动）。
为免互相覆盖，遵守以下约定：

1. **只提交自己改的文件**：`git add <显式路径>`，**不要用 `git add -A` / `git add .`**。
   `git add -A` 会把其它会话**在飞未完成**的改动一起提交（本项目已经因此提交过一次他人在飞的改动）。
2. **提交前先看状态**：`git status` + `git log --oneline -3 origin/main`，确认没有别人的新提交或被自己误加的文件。
3. **共享文件串行修改**（同一时间只允许一个会话改）：
   `frontend/app/api/kaijiang/[[...path]]/route.ts`、`frontend/lib/prediction-contract.ts`、
   `frontend/public/vendor/*/site-data-adapter.js`、`frontend/lib/<site>-*.ts`、
   `docs/prediction-display-standard.md`、`DEPLOY.md`、`AGENTS.md`。
   发现别人正在改（`git status` 里有非自己的改动、或 mtime 很近）就先做别的，或只在自己那份文件上干活。
4. **发布前先 `git fetch`**，用部署脚本的 `git merge --ff-only`（脚本已如此），**不要强推、不要 `reset --hard`**。
   若 `origin/main` 已包含他人新提交，部署会把它们一起带上线——发布后要按下面的验收跑一遍。
5. **未经验证的第三方改动不要提交**：发现回归（例如展示审计 `error` 由 0 变正）先 **revert**，
   在报告/DEPLOY.md 里记录「谁改的、什么回归、已回退」，不要沉默覆盖。
6. **每轮改动的固定验收**（见 `docs/prediction-display-standard.md`）：
   - 本地预检：`python scripts\audit-prediction-display.py <site> --base-url http://127.0.0.1:3000 --json <out>`
   - 线上审计：`python scripts\audit-prediction-display.py --json <out>`（要求 `error=0`、`js_errors=0`）
   - 后端：`cd backend/src; python -m pytest -q`
   - 前端契约：`node frontend/test/<相关>.mjs`
7. **改动落库前先合并**：本地 dev 与 `origin/main` 出现分叉时，先同步再改，避免基于过期代码做判断。

