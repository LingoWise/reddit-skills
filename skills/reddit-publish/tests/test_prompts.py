import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import prompts


def test_prompts_defined():
    assert "{topic}" in prompts.RESEARCH_PROMPT
    assert "{style}" in prompts.DRAFT_PROMPT
    assert "{corpus}" in prompts.SUBREDDIT_SUGGEST_PROMPT
