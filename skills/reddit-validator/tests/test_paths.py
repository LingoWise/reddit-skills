from pipeline.paths import skill_dir, reports_dir, checkpoints_dir, logs_dir


def test_skill_dir_is_reddit_validator():
    assert skill_dir().name == "reddit-validator"


def test_directories_exist_and_are_under_skill_dir():
    for directory_fn in (reports_dir, checkpoints_dir, logs_dir):
        d = directory_fn()
        assert d.exists()
        assert d.is_dir()
        assert d.relative_to(skill_dir())
