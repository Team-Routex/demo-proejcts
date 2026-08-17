"""
Project management commands — Django-style scripts, the Raft way.

Put modules under your project's ``commands/`` folder and run them with::

    raft run seed
    raft run --help

Example ``commands/seed.py``::

    from raft.commands import command

    @command(help="Populate demo data")
    def seed():
        print("Seeding...")
"""

from raft.commands.decorators import command
from raft.commands.discovery import discover_commands, get_command, list_command_names

__all__ = [
    "command",
    "discover_commands",
    "get_command",
    "list_command_names",
]
