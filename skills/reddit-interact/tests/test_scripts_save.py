import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts import save


def test_save_dry_run(capsys):
    code = save.main(["t3_abc", "--dry-run"])
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["event"] == "done"
    assert out["dry_run"] is True
    assert out["action"] == "save"


def test_unsave_dry_run(capsys):
    code = save.main(["t3_abc", "--unsave", "--dry-run"])
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["event"] == "done"
    assert out["dry_run"] is True
    assert out["action"] == "unsave"
