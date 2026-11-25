import io

from fuze import cli, config


def test_run_refuses_other_modes(capsys):
    assert cli.main(["run", "--mode", "mainnet"]) == 2
    assert "Only \"dry\" mode" in capsys.readouterr().out


def test_flags_and_init(fuze_home):
    assert cli.main(["init"]) == 0
    cli.main(["pause"])
    cli.main(["flatten"])
    assert (fuze_home / "PAUSE").exists() and (fuze_home / "FLATTEN").exists()
    cli.main(["resume"])
    cli.main(["unflatten"])
    assert not (fuze_home / "PAUSE").exists() and not (fuze_home / "FLATTEN").exists()


def test_lowering_is_free_raising_needs_a_terminal(fuze_home, monkeypatch, capsys):
    cli.main(["init"])
    monkeypatch.setattr("sys.stdin", io.StringIO("RAISE\n"))  # not a TTY
    assert cli.main(["limits", "--max-x", "2"]) == 0
    assert cli.main(["limits", "--max-x", "4"]) == 2
    assert "not a terminal" in capsys.readouterr().out
    assert cli.main(["limits", "--stale-flat-min", "30"]) == 0  # turning it on lowers risk
    assert cli.main(["limits", "--stale-flat-min", "off"]) == 2
    assert config.load()["max_x"] == 2.0 and config.load()["stale_flat_min"] == 30.0


def test_raising_on_a_tty_needs_typed_confirmation(fuze_home, monkeypatch):
    cli.main(["init"])

    class Tty(io.StringIO):
        def isatty(self):
            return True

    monkeypatch.setattr("sys.stdin", Tty())
    monkeypatch.setattr("builtins.input", lambda _: "yes")
    assert cli.main(["limits", "--scale", "0.5"]) == 1 and config.load()["scale"] == 0.1
    monkeypatch.setattr("builtins.input", lambda _: "RAISE")
    assert cli.main(["limits", "--scale", "0.5"]) == 0 and config.load()["scale"] == 0.5


def test_bad_limit_value(fuze_home):
    cli.main(["init"])
    assert cli.main(["limits", "--max-x", "100"]) == 2
    assert cli.main(["limits", "--scale", "nan"]) == 2
