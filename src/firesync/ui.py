"""User interface utilities for FireSync CLI."""

import sys
from typing import Dict


def confirm_apply(
    changes_summary: Dict[str, int],
    project_id: str,
    env_name: str,
    auto_approve: bool = False,
) -> bool:
    """
    Ask user for confirmation before applying changes to Firestore.

    Args:
        changes_summary: Dictionary with counts of create/delete/update operations
        project_id: GCP project ID
        env_name: Environment name
        auto_approve: If True, skip confirmation prompt

    Returns:
        True if user confirmed or auto_approve is True, False otherwise
    """
    if auto_approve:
        return True

    # Calculate total changes
    total_changes = sum(changes_summary.values())

    if total_changes == 0:
        print("[~] No changes to apply")
        return False

    # Display what will be changed
    print(f"\n[!] This will modify Firestore in GCP project: {project_id}")
    print(f"    Environment: {env_name}")

    if changes_summary.get("create", 0) > 0:
        print(f"    [+] {changes_summary['create']} resources will be created")
    if changes_summary.get("delete", 0) > 0:
        print(f"    [-] {changes_summary['delete']} resources will be deleted")
    if changes_summary.get("update", 0) > 0:
        print(f"    [~] {changes_summary['update']} resources will be updated")

    # Warn if production environment
    if "prod" in env_name.lower():
        print("\n    WARNING: This is a PRODUCTION environment!")

    # Ask for confirmation
    print()
    try:
        response = input("Continue? [y/N]: ").strip().lower()
        return response in ("y", "yes")
    except (KeyboardInterrupt, EOFError):
        print("\n[!] Operation cancelled")
        return False


def calculate_changes(diff: Dict) -> Dict[str, int]:
    """
    Calculate summary of changes from diff dictionary.

    Args:
        diff: Dictionary with 'create', 'delete', 'update' keys

    Returns:
        Dictionary with counts for each operation type
    """
    return {
        "create": len(diff.get("create", [])),
        "delete": len(diff.get("delete", [])),
        "update": len(diff.get("update", [])),
    }
