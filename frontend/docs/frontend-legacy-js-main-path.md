# Frontend Legacy JS Main Path

## Current Decision

The current foreground display path uses the legacy HTML + JS + CSS frontend, not the old React homepage chain.

## Main Request Flow

```text
User visits /
  -> app/page.tsx
  -> /?t=3
  -> proxy.ts
  -> next.config.mjs rewrite
  -> /vendor/shengshi8800/embed.html?type=3&web=4
  -> public/vendor/shengshi8800/embed.html
  -> public/vendor/shengshi8800/index.html
  -> public/vendor/shengshi8800/static/js/*.js
```

Old-style entry URLs such as `/?type=3&web=4` and `/vendor/shengshi8800/embed.html?type=3&web=4`
are permanently redirected to the canonical `/?t=3` form.

## API Flow

```text
Legacy JS
  -> /api/kaijiang/*
  -> /api/latest-draw
  -> /api/next-draw-deadline
  -> /api/post/getList
  -> /uploads/image/*
  -> app/api/**/route.ts
  -> Python backend
```

## Scope Rules

1. React homepage files are no longer maintained as the main path.
2. `app/api/**/route.ts` remains part of the active runtime chain.
3. `_archived_unused_frontend/` is the archive area and does not participate in build or lint checks.
4. Future React migration must be incremental by module.
5. Do not rewrite all legacy JS modules into React at once.
