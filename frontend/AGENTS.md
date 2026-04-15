<!-- BEGIN:nextjs-agent-rules -->
# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code. Heed deprecation notices.
<!-- END:nextjs-agent-rules -->

Read [../.claude/AGENTS.md](/Users/max/Zima/.claude/AGENTS.md) first.

## Scope

- `frontend/src/`
- `frontend/public/`
- `frontend/package.json`

## Run

```bash
cd frontend
npm install
npm run dev
```

## Verification

```bash
cd frontend
npm run lint
npm run build
```

## Frontend Invariants

- Keep the existing Next.js app-router structure.
- Prefer repo patterns over generic Next.js defaults.
- Coordinate with backend API paths through `NEXT_PUBLIC_API_URL` and `INTERNAL_API_URL`.
