import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts import upvote, downvote


def test_upvote_dry_run(capsys):
    code = upvote.main(["t3_abc", "--dry-run"])
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["event"] == "done"
    assert out["dry_run"] is True
    assert out["action"] == "upvote"


def test_downvote_dry_run(capsys):
    code = downvote.main(["t3_abc", "--dry-run"])
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["event"] == "done"
    assert out["dry_run"] is True
    assert out["action"] == "downvote"


def test_upvote_dry_run_comment(capsys):
    code = upvote.main(["t1_c1", "--dry-run"])
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["thing_id"] == "t1_c1"
