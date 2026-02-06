from __future__ import annotations

from omada_batch.storage.file_change_log import sync_git_worktree_to_changelog


def main() -> None:
    count = sync_git_worktree_to_changelog()
    print(f"changelog entries written: {count}")


if __name__ == "__main__":
    main()
