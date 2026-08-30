import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts import comment


def test_comment_dry_run(capsys):
    code = comment.main(["t3_abc", "--text", "Hello", "--dry-run"])
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["event"] == "done"
    assert out["dry_run"] is True
    assert out["action"] == "comment"


def test_comment_text_file(tmp_path, capsys):
    text_file = tmp_path / "comment.txt"
    text_file.write_text("From file body")
    code = comment.main(["t3_abc", "--text-file", str(text_file), "--dry-run"])
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["text"] == "From file body"


def test_comment_missing_text(capsys):
    code = comment.main(["t3_abc", "--dry-run"])
    assert code == 1
    out = json.loads(capsys.readouterr().out)
    assert out["code"] == "text_missing"
