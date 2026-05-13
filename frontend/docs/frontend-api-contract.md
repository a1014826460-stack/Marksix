# Frontend API Contract

## Active Foreground Path

The active display frontend is `public/vendor/shengshi8800/**`.
Legacy JS calls same-origin Next.js API routes, and those routes proxy or adapt requests for the Python backend.

## Core Routes To Keep

- `app/api/kaijiang/[[...path]]/route.ts`
- `app/api/post/getList/route.ts`
- `app/api/latest-draw/route.ts`
- `app/api/next-draw-deadline/route.ts`
- `app/api/draw-history/route.ts`
- `app/api/lottery-data/route.ts`
- `app/api/predict/[mechanism]/route.ts`
- `app/uploads/image/[bucket]/[filename]/route.ts`

## Compatibility Rule

Do not change legacy response formats unless needed to fix a clear bug.
