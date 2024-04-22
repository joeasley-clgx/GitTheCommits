from dataclasses import dataclass


@dataclass
class CommitDetailVisibility(object):
    """Stores what commit details will be visible."""

    message: bool = False
    item_number: bool = False
    author: bool = False
    date: bool = False
    commit_url: bool = False
    pull_request_url: bool = False
    sha: bool = False
    is_merge_commit: bool = False
    show_cherry_pick_command: bool = False
    