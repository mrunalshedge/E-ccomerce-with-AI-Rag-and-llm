"""Create an admin account (admins cannot self-register through the API).

Usage (from backend/):  python -m app.scripts.create_admin --name "Admin" --email admin@example.com
The password is prompted for, never passed on the command line.
"""

import argparse
import asyncio
import getpass
import sys

from pydantic import ValidationError

from app.core.errors import ConflictError
from app.db.init_db import init_db
from app.db.session import SessionLocal, engine
from app.models.user import UserRole
from app.schemas.user import UserCreate
from app.services.user_service import create_user


async def _main(name: str, email: str, password: str) -> int:
    try:
        # Validate as a customer (admins are blocked in the public schema), then override the role.
        data = UserCreate(name=name, email=email, password=password)
    except ValidationError as exc:
        print(exc, file=sys.stderr)
        return 1

    await init_db(engine)
    try:
        async with SessionLocal() as db:
            user = await create_user(db, data, role=UserRole.ADMIN)
    except ConflictError as exc:
        print(f"Error: {exc.detail}", file=sys.stderr)
        return 1
    finally:
        await engine.dispose()

    print(f"Admin created: id={user.id} email={user.email}")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--name", required=True)
    parser.add_argument("--email", required=True)
    args = parser.parse_args()

    password = getpass.getpass("Password: ")
    if password != getpass.getpass("Confirm password: "):
        sys.exit("Passwords do not match")
    sys.exit(asyncio.run(_main(args.name, args.email, password)))


if __name__ == "__main__":
    main()
