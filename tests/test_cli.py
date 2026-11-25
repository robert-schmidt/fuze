import io

import pytest

from fuze import cli, config


class Tty(io.StringIO):
    def isatty(self):
        return True


def answers(monkeypatch, *replies):
    """A terminal on stdin; input() returns these replies in order and fails if asked more."""
    it = iter(replies)
    monkeypatch.setattr("sys.stdin", Tty())
    monkeypatch.setattr("builtins.input", lambda _: next(it))


def test_run_refuses_other_modes(capsys):
    assert cli.main(["run", "--mode", "mainnet"]) == 2  # the mode is a setting, changed only with `fuze mode`
    assert "fuze mode mainnet" in capsys.readouterr().out


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
    monkeypatch.setattr("sys.stdin", Tty())
    monkeypatch.setattr("builtins.input", lambda _: "yes")
    assert cli.main(["limits", "--percent", "50"]) == 1 and config.load()["percent"] == 10.0
    monkeypatch.setattr("builtins.input", lambda _: "RAISE")
    assert cli.main(["limits", "--percent", "50"]) == 0 and config.load()["percent"] == 50.0


def test_bad_limit_value(fuze_home):
    cli.main(["init"])
    assert cli.main(["limits", "--max-x", "100"]) == 2
    assert cli.main(["limits", "--percent", "nan"]) == 2
    assert cli.main(["limits", "--daily-loss", "0.1"]) == 2  # in percent now: 10 means 10%
    assert cli.main(["limits", "--max-position-usd", "lots"]) == 2
    assert config.load() == config.validate({})


# --- setting it up --------------------------------------------------------------------------------------------------

def test_init_with_flags_no_terminal(fuze_home, capsys):
    assert cli.main(["init", "--size-mode", "fixed", "--fixed-usd", "500", "--max-position-usd", "800",
                     "--max-x", "2", "--daily-loss", "5"]) == 0
    cfg = config.load()
    assert (cfg["mode"], cfg["size_mode"], cfg["fixed_usd"], cfg["max_position_usd"], cfg["max_x"],
            cfg["daily_loss_frac"]) == ("simulation", "fixed", 500.0, 800.0, 2.0, 0.05)
    assert "$800 of Bitcoin ($900 before your caps)" in capsys.readouterr().out


def test_init_without_flags_or_terminal_writes_safe_defaults(fuze_home, capsys):
    assert cli.main(["init"]) == 0
    assert config.load() == config.validate({})
    assert "$180 of Bitcoin" in capsys.readouterr().out


def test_init_never_overwrites_without_force(fuze_home, monkeypatch):
    assert cli.main(["init", "--percent", "5"]) == 0
    assert cli.main(["init", "--percent", "8"]) == 1  # flags given but not applied: say so with the exit code
    assert cli.main(["init"]) == 0
    assert config.load()["percent"] == 5.0
    assert cli.main(["init", "--force", "--percent", "3"]) == 0  # lower: no confirmation needed
    assert config.load()["percent"] == 3.0
    assert cli.main(["init", "--force", "--yes", "--percent", "50"]) == 2  # higher: --yes is not a confirmation
    assert config.load()["percent"] == 3.0
    answers(monkeypatch, "RAISE")
    assert cli.main(["init", "--force", "--yes", "--percent", "50"]) == 0 and config.load()["percent"] == 50.0


def test_init_force_starts_in_simulation(fuze_home):
    config.ensure_home()
    (fuze_home / "config.json").write_text('{"mode": "warp"}')  # not valid: compared with the defaults
    assert cli.main(["init", "--force"]) == 0 and config.load()["mode"] == "simulation"


def test_init_force_refuses_while_in_a_live_mode(fuze_home):
    config.save({**config.DEFAULTS, "mode": "mainnet", "mainnet_account": 5})
    assert cli.main(["init", "--force"]) == 2 and config.load()["mode"] == "mainnet"


def test_init_asks_on_a_terminal(fuze_home, monkeypatch, capsys):
    answers(monkeypatch, "", "fixed", "250", "none", "", "5", "")  # first: the mode, Enter keeps simulation
    assert cli.main(["init"]) == 0
    cfg = config.load()
    assert (cfg["size_mode"], cfg["fixed_usd"], cfg["max_position_usd"], cfg["max_x"], cfg["daily_loss_frac"]) \
        == ("fixed", 250.0, None, 3.0, 0.05)
    assert "$450 of Bitcoin" in capsys.readouterr().out


def test_init_asks_again_after_a_bad_answer_and_can_be_declined(fuze_home, monkeypatch, capsys):
    answers(monkeypatch, "", "", "500", "abc", "20", "", "", "", "n")
    assert cli.main(["init"]) == 1 and not (fuze_home / "config.json").exists()
    out = capsys.readouterr().out
    assert "between 1 and 100" in out and "not a number" in out and "Not saved" in out


def test_init_yes_on_a_terminal_asks_nothing(fuze_home, monkeypatch):
    answers(monkeypatch)  # any question would fail
    assert cli.main(["init", "--yes", "--percent", "7"]) == 0 and config.load()["percent"] == 7.0


# --- adjusting: every change that can raise risk needs RAISE typed at a terminal ----------------------------------

START = ["--percent", "10", "--fixed-usd", "50", "--max-position-usd", "500", "--max-x", "3", "--daily-loss", "10",
         "--stale-flat-min", "30"]


@pytest.mark.parametrize("flags", [
    ["--percent", "20"],
    ["--fixed-usd", "60"],
    ["--max-position-usd", "600"],
    ["--max-position-usd", "off"],
    ["--max-x", "4"],
    ["--daily-loss", "20"],
    ["--stale-flat-min", "off"],
])
def test_every_raise_needs_confirmation(fuze_home, monkeypatch, capsys, flags):
    cli.main(["init"])
    assert cli.main(["limits"] + START) == 0  # START only lowers the defaults
    before = config.load()
    monkeypatch.setattr("sys.stdin", io.StringIO("RAISE\n"))
    assert cli.main(["limits"] + flags) == 2 and config.load() == before
    assert "not a terminal" in capsys.readouterr().out
    answers(monkeypatch, "raise")
    assert cli.main(["limits"] + flags) == 1 and config.load() == before
    answers(monkeypatch, "RAISE")
    assert cli.main(["limits"] + flags) == 0 and config.load() != before


def test_switching_mode_to_a_larger_position_needs_confirmation(fuze_home, monkeypatch):
    cli.main(["init", "--size-mode", "fixed", "--fixed-usd", "50"])
    monkeypatch.setattr("sys.stdin", io.StringIO(""))
    assert cli.main(["limits", "--size-mode", "percent"]) == 2  # 10% of $1,000 = $100 > $50
    assert config.load()["size_mode"] == "fixed"
    assert cli.main(["limits", "--size-mode", "percent", "--percent", "4"]) == 0  # $40 < $50
    assert config.load()["size_mode"] == "percent"


def test_lowering_needs_no_confirmation(fuze_home, monkeypatch):
    cli.main(["init"])
    monkeypatch.setattr("sys.stdin", io.StringIO(""))
    for flags in (["--percent", "5"], ["--fixed-usd", "20"], ["--max-position-usd", "300"], ["--max-x", "1"],
                  ["--daily-loss", "3"], ["--size-mode", "fixed"], ["--max-position-usd", "200"]):
        assert cli.main(["limits"] + flags) == 0, flags
    cfg = config.load()
    assert (cfg["size_mode"], cfg["fixed_usd"], cfg["max_position_usd"]) == ("fixed", 20.0, 200.0)


def test_limits_shows_the_sizing(fuze_home, capsys):
    cli.main(["init", "--percent", "20"])
    capsys.readouterr()
    assert cli.main(["limits"]) == 0
    assert "20% of your balance" in capsys.readouterr().out


def test_ctrl_d_at_a_question_saves_nothing(fuze_home, monkeypatch):
    monkeypatch.setattr("sys.stdin", Tty())

    def eof(_):
        raise EOFError

    monkeypatch.setattr("builtins.input", eof)
    assert cli.main(["init"]) == 1 and not (fuze_home / "config.json").exists()
