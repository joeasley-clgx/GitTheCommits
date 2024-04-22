from dataclasses import dataclass
from datetime import datetime


@dataclass
class CommitInfo(object):
    """Stores the commit info we care about."""
    
    message: str
    author: str
    date: datetime
    sha: str
    commit_url: str
    pr_url: str
    item_number: str
    is_merge: bool
    