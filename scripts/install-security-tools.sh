#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
[[ "$(uname -s)-$(uname -m)" == Linux-x86_64 ]] || { echo 'Pinned installer supports Linux x86_64; install matching releases manually.'; exit 1; }
mkdir -p .cache/bin
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
curl -fsSL https://github.com/gitleaks/gitleaks/releases/download/v8.30.1/gitleaks_8.30.1_linux_x64.tar.gz -o "$work/gitleaks.tar.gz"
curl -fsSL https://github.com/aquasecurity/trivy/releases/download/v0.76.1/trivy_0.76.1_Linux-64bit.tar.gz -o "$work/trivy.tar.gz"
(cd "$work"; printf '%s  %s\n' 551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb gitleaks.tar.gz c7cbe3137fb8a48a17574bede3dd6beb16742d1e9772929940fc90082c39d9c0 trivy.tar.gz | sha256sum -c -)
tar xzf "$work/gitleaks.tar.gz" -C .cache/bin gitleaks
tar xzf "$work/trivy.tar.gz" -C .cache/bin trivy
