import fs from "node:fs"

const page = fs.readFileSync(
  "features/forced-announcements/ForcedAnnouncementsPage.tsx",
  "utf8",
)

for (const token of [
  "/admin/forced-announcements",
  "all_sites",
  "selected_sites",
  "site_ids",
  'type="datetime-local"',
  "starts_at",
  "ends_at",
]) {
  if (!page.includes(token)) {
    throw new Error(`forced announcement management contract missing: ${token}`)
  }
}

if (page.includes("dangerouslySetInnerHTML")) {
  throw new Error("unsanitized announcement drafts must not execute in the admin page")
}

const route = fs.readFileSync("app/forced-announcements/page.tsx", "utf8")
if (!route.includes("ForcedAnnouncementsPage")) {
  throw new Error("forced announcement route is not wired")
}

const shell = fs.readFileSync("components/admin/admin-shell.tsx", "utf8")
if (!shell.includes('href: "/forced-announcements"')) {
  throw new Error("forced announcement navigation entry is not wired")
}

