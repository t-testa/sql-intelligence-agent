"""Create local-only random credentials without printing or overwriting secrets."""

import secrets
from pathlib import Path


def main() -> None:
    target = Path(".env")
    if target.exists():
        raise SystemExit(".env already exists; leaving it unchanged")
    template = Path(".env.example").read_text(encoding="utf-8")
    for name in ("LOCAL_API_TOKEN", "SQL_PASSWORD", "SQL_ADMIN_PASSWORD"):
        template = template.replace(f"{name}=\n", f"{name}=Sia!{secrets.token_hex(24)}\n")
    target.write_text(template, encoding="utf-8")
    print("Created .env with unique local credentials. Keep this file private and untracked.")


if __name__ == "__main__":
    main()
