"""Where things live. Everything under work/ is downloaded or generated and never committed."""
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORK = os.path.join(REPO, "work")
RESULTS = os.path.join(REPO, "results")
DBS = os.path.join(WORK, "dbs")            # update_all database files
HIST = os.path.join(WORK, "hist")          # history-only clones of core repos
PINNED = os.path.join(WORK, "pinned")      # source checked out at each build's commit
MRAS = os.path.join(WORK, "mras")          # MRA files the databases ship
MAME_REPO = os.path.join(WORK, "mame")
MAME = os.path.join(MAME_REPO, "src", "mame")
MANIFEST = os.path.join(WORK, "manifest.json")


def jt_checkout(commit):
    """jtcores checked out at one commit (a worktree of work/pinned/jtcores): JT builds from different
    releases are pinned to different commits."""
    return os.path.join(PINNED, "jtcores@" + commit[:10])


for d in (WORK, RESULTS):
    os.makedirs(d, exist_ok=True)
