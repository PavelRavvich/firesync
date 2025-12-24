"""FireSync CLI commands."""

from firesync.commands.init import main as init_main
from firesync.commands.pull import main as pull_main
from firesync.commands.plan import main as plan_main
from firesync.commands.apply import main as apply_main
from firesync.commands.env import main as env_main

__all__ = ["init_main", "pull_main", "plan_main", "apply_main", "env_main"]
