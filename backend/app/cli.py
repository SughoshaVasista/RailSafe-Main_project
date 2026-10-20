"""AMRIN backend management commands."""

import argparse

from app.config import Settings
from app.db.session import build_engine, build_session_factory
from app.services.demo_seed import seed_demo


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    parser.add_argument("command", choices=["seed-demo"])
    args = parser.parse_args()

    if args.command == "seed-demo":
        engine = build_engine(Settings().database_url)
        session_factory = build_session_factory(engine)
        with session_factory.begin() as session:
            counts = seed_demo(session)
        engine.dispose()
        inserted = sum(counts.values())
        print(f"Demo seed complete: {inserted} records inserted across {len(counts)} record types.")


if __name__ == "__main__":
    main()
