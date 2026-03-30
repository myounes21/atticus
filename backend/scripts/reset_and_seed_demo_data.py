"""Convenience entrypoint for resetting and reseeding demo data."""

from __future__ import annotations

from backend.scripts.reset_demo_data import main as reset_demo_data
from backend.scripts.seed_demo_data import main as seed_demo_data


def main() -> None:
    reset_demo_data()
    seed_demo_data()


if __name__ == "__main__":
    main()
