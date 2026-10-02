# Infrastructure

Do not provision cloud without an explicit task. Never use real credentials or production data.
Use reproducible configuration and pinned image tags/digests; future cloud resources require IaC.
Keep database tests isolated and disposable; never reset application volumes in test automation.
Bind local admin endpoints to loopback. Production deployment needs separate auth/secrets/TLS design.
Validate Compose rendering, images, health conditions and migrations before reporting success.
When Docker is unavailable in Codex Cloud, report these infrastructure checks as `CI REQUIRED`;
only the canonical GitHub Actions full-validation workflow can close them.
