import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts import reply


def test_reply_dry_run(capsys):
    code = reply.main(["t1_c1", "--text", "Reply body", "--dry-run"])
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["event"] == "done"
    assert out["dry_run"] is True
    assert out["action"] == "reply"


def test_reply_text_file(tmp_path, capsys):
    text_file = tmp_path / "reply.txt"
    text_file.write_text("Reply from file")
    code = reply.main(["t1_c1", "--text-file", str(text_file), "--dry-run"])
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["text"] == "Reply from file"


def test_reply_missing_text(capsys):
    code = reply.main(["t1_c1", "--dry-run"])
    assert code == 1
    out = json.loads(capsys.readouterr().out)
    assert out["code"] == "text_missing"
