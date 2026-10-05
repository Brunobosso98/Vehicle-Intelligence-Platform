"""Hash the exact reviewable working tree without printing file contents."""

import hashlib
import subprocess
from pathlib import Path


def main() -> None:
    paths = (
        subprocess.check_output(
            ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"]
        )
        .decode()
        .split("\0")
    )
    digest = hashlib.sha256()
    for name in sorted(set(paths) - {""}):
        path = Path(name)
        digest.update(name.encode() + b"\0")
        digest.update(path.read_bytes() if path.is_file() else b"<missing>")
        digest.update(b"\0")
    print(digest.hexdigest())


if __name__ == "__main__":
    main()
