# Legacy JS Shell Plan

## Current Status

The active foreground path is now the legacy HTML + JS + CSS site.

- Main entry: `/` -> `/vendor/shengshi8800/embed.html?type=3&web=4`
- Canonical public entry: `/?t=1|2|3`
- Active frontend assets: `public/vendor/shengshi8800/**`
- API compatibility layer: `app/api/**/route.ts`
- Optional shell: `app/legacy-shell/page.tsx` remains for iframe fallback/debug only

## Architecture

```text
User
  -> /
  -> app/page.tsx
  -> /?t=3
  -> proxy.ts
  -> next.config.mjs rewrite
  -> /vendor/shengshi8800/embed.html?type=3&web=4
  -> public/vendor/shengshi8800/embed.html
  -> public/vendor/shengshi8800/index.html
  -> public/vendor/shengshi8800/static/js/*.js
  -> /api/kaijiang/*, /api/latest-draw, /api/post/getList, /uploads/image/*
  -> app/api/**/route.ts
  -> lib/backend-api.ts or route-local adapter logic
  -> Python backend
```

## Migration Rule

If React migration resumes later, it must be done module by module. Do not rewrite the full legacy site in one pass.
