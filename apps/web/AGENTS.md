# Web

App Router and strict TypeScript. Server Components by default; client components only for interaction.
The browser calls the same-origin /api/status proxy; private API addresses are server-only.
Use generated contract types; no manual copies and no unexplained any.
Provide loading, failure and retry states. Use semantic HTML, labels, focus and sufficient contrast.
Run `make check-web`; run E2E for changes to the complete status flow. Keep secrets off client bundles.
Backend owns Phase 0 OTel instrumentation; proxy failures return sanitized operational states.
