# Web

App Router and strict TypeScript. Server Components by default; client components only for interaction.
The browser calls the same-origin /api/status proxy; private API addresses are server-only.
Use generated contract types; no manual copies and no unexplained any.
Provide loading, failure and retry states. Use semantic HTML, labels, focus and sufficient contrast.
Run `make check-web`; run E2E for changes to the complete status flow. Keep secrets off client bundles.
Backend owns Phase 0 OTel instrumentation; proxy failures return sanitized operational states.

<!-- BEGIN:nextjs-agent-rules -->

## This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->
