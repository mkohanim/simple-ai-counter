import os
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from counter_core import CounterCore, INT32_MAX, INT32_MIN  # noqa: E402


def test_defaults_and_tick_only_when_running():
    c = CounterCore()
    assert c.snapshot() == (0, 1, False)
    assert c.tick() is False
    c.start()
    assert c.tick() is True
    assert c.count == 1
    c.stop()
    assert c.tick() is False
    assert c.count == 1


def test_tick_adds_one_regardless_of_step():
    c = CounterCore()
    c.set_step(500)
    c.start()
    c.tick()
    assert c.count == 1


def test_increment_decrement_use_step():
    c = CounterCore()
    c.set_step(10)
    c.increment()
    c.increment()
    c.decrement()
    assert c.count == 10
    c.decrement()
    c.decrement()
    assert c.count == -10


def test_clamps_at_int32_limits():
    c = CounterCore()
    c._count = INT32_MAX - 1
    c.set_step(5)
    c.increment()
    assert c.count == INT32_MAX
    c.start()
    c.tick()
    assert c.count == INT32_MAX
    c._count = INT32_MIN + 1
    c.decrement()
    assert c.count == INT32_MIN


@pytest.mark.parametrize('bad', [0, -1, 18001, 'abc', None, 2.5, float('nan'), float('inf')])
def test_set_step_rejects_invalid(bad):
    c = CounterCore()
    with pytest.raises(ValueError):
        c.set_step(bad)
    assert c.step == 1


@pytest.mark.parametrize('good', [1, 18000, '250', 7.0])
def test_set_step_accepts_valid(good):
    c = CounterCore()
    c.set_step(good)
    assert c.step == int(float(good))


def test_persistence_round_trip(tmp_path):
    path = str(tmp_path / 'state' / 'counter_state.json')
    c = CounterCore(state_file=path)
    c.set_step(42)
    c.increment()
    c.increment()
    c.save()
    c2 = CounterCore(state_file=path)
    assert c2.count == 84
    assert c2.step == 42
    assert c2.running is False


def test_corrupt_state_file_falls_back_to_defaults(tmp_path):
    path = tmp_path / 'counter_state.json'
    path.write_text('not json')
    c = CounterCore(state_file=str(path))
    assert c.snapshot() == (0, 1, False)


def test_on_change_called():
    calls = []
    c = CounterCore(on_change=lambda: calls.append(1))
    c.start()
    c.tick()
    c.increment()
    assert len(calls) == 3


def test_background_thread_counts_and_stops():
    c = CounterCore(tick_seconds=0.05)
    c.begin()
    time.sleep(0.6)
    assert c.running is True
    assert c.count >= 3
    c.shutdown()
    assert c.running is False
    frozen = c.count
    time.sleep(0.2)
    assert c.count == frozen
