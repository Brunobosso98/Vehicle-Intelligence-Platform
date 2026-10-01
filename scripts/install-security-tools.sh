#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
[[ "$(uname -s)-$(uname -m)" == Linux-x86_64 ]] || { echo 'Pinned installer supports Linux x86_64; install matching releases manually.'; exit 1; }
mkdir -p .cache/bin
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
curl -fsSL https://github.com/gitleaks/gitleaks/releases/download/v8.30.1/gitleaks_8.30.1_linux_x64.tar.gz -o "$work/gitleaks.tar.gz"
curl -fsSL https://github.com/aquasecurity/trivy/releases/download/v0.75.0/trivy_0.75.0_Linux-64bit.tar.gz -o "$work/trivy.tar.gz"
(cd "$work"; printf '%s  %s\n' 551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb gitleaks.tar.gz c6e65abddb348e25f10549df887045629cf28cc72453cd1c63acb717316b3f3f trivy.tar.gz | sha256sum -c -)
tar xzf "$work/gitleaks.tar.gz" -C .cache/bin gitleaks
tar xzf "$work/trivy.tar.gz" -C .cache/bin trivy
