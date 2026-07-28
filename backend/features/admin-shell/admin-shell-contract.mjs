import fs from "node:fs"

const source = fs.readFileSync("components/admin/admin-shell.tsx", "utf8")

for (const token of ["localStorage", "onPointerDown", "onPointerMove", "SIDEBAR_MIN_WIDTH", "SIDEBAR_MAX_WIDTH"]) {
  if (!source.includes(token)) throw new Error(`resizable sidebar contract missing: ${token}`)
}

const adminApi = fs.readFileSync("lib/admin-api.ts", "utf8")
for (const token of ["response.status === 401", "redirectToLoginAfterSessionExpiry", "window.location.replace"]) {
  if (!adminApi.includes(token)) throw new Error(`expired-session redirect contract missing: ${token}`)
}

const draws = fs.readFileSync("features/draws/DrawsPage.tsx", "utf8")
if (!draws.includes("row.is_opened ?")) {
  throw new Error("opened draw actions must be conditionally disabled")
}

const layout = fs.readFileSync("app/layout.tsx", "utf8")
if (!layout.includes('"/fackyou/favicon.ico"')) {
  throw new Error("admin metadata must reference the deployed favicon path")
}
