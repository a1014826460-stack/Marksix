# Deployment Authorization

- Do not connect to any server, run `git pull` or `git push` remotely, transfer files, build or restart remote services, run migrations, inspect remote state, or otherwise perform remote operations unless the user explicitly authorizes the server and the requested operation in the current message.
- A previous deployment authorization does not authorize later server access. Ask for a new explicit instruction before every separate remote operation.
