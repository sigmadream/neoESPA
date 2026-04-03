import argparse

from sqlmodel import Session

from .core.db import engine
from .core.migrations import apply_migrations
from .services.user_management import UserManagementError, create_admin_user


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="neoESPA backend administration CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_admin_parser = subparsers.add_parser(
        "create-admin",
        help="Create a local admin account",
    )
    create_admin_parser.add_argument("--id", dest="user_id", required=True, help="Login ID")
    create_admin_parser.add_argument("--sid", type=int, required=True, help="Student or staff ID")
    create_admin_parser.add_argument("--name", required=True, help="Display name")
    create_admin_parser.add_argument("--phone", required=True, help="Phone number")
    create_admin_parser.add_argument("--email", required=True, help="Email address")
    create_admin_parser.add_argument("--password", required=True, help="Initial password")
    create_admin_parser.add_argument(
        "--inactive",
        action="store_true",
        help="Create the account in a disabled state",
    )

    return parser


def _run_create_admin(args: argparse.Namespace) -> int:
    apply_migrations(engine)

    with Session(engine) as session:
        user = create_admin_user(
            session,
            user_id=args.user_id,
            sid=args.sid,
            password=args.password,
            name=args.name,
            phone=args.phone,
            email=args.email,
            is_active=not args.inactive,
        )
        session.add(user)
        session.commit()
        session.refresh(user)

    print(
        f"Created admin user '{user.id}' "
        f"(sid={user.sid}, active={str(user.is_active).lower()})"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "create-admin":
            return _run_create_admin(args)
    except UserManagementError as error:
        parser.exit(1, f"Error: {error}\n")

    parser.exit(1, f"Error: unsupported command '{args.command}'\n")


if __name__ == "__main__":
    raise SystemExit(main())
