"""Counter logic with no udi_interface dependency, so it can be unit tested."""
import json
import logging
import os
import threading
import time

LOGGER = logging.getLogger(__name__)

INT32_MIN = -2147483648
INT32_MAX = 2147483647
STEP_MIN = 1
STEP_MAX = 18000


def _clamp(value, lo, hi):
    return max(lo, min(hi, value))


class CounterCore:
    """A signed 32-bit counter that ticks +1 per interval while running.

    Increment/Decrement move it by the step size. Values clamp at the signed
    32-bit limits rather than wrapping. count and step persist to state_file;
    the running flag does not (the counter always starts running).
    """

    def __init__(self, state_file=None, on_change=None, tick_seconds=1.0, save_every=30.0):
        self._lock = threading.RLock()
        self._save_lock = threading.Lock()
        self._stop_evt = threading.Event()
        self._thread = None
        self._state_file = state_file
        self._on_change = on_change
        self._interval = float(tick_seconds)
        self._save_every = float(save_every)
        self._count = 0
        self._step = 1
        self._running = False
        self._load()

    # ---- state -------------------------------------------------------
    def snapshot(self):
        with self._lock:
            return self._count, self._step, self._running

    @property
    def count(self):
        return self.snapshot()[0]

    @property
    def step(self):
        return self.snapshot()[1]

    @property
    def running(self):
        return self.snapshot()[2]

    def _load(self):
        if not self._state_file:
            return
        try:
            with open(self._state_file, 'r') as f:
                data = json.load(f)
            count = _clamp(int(data.get('count', 0)), INT32_MIN, INT32_MAX)
            step = _clamp(int(data.get('step', 1)), STEP_MIN, STEP_MAX)
        except FileNotFoundError:
            return
        except Exception:
            LOGGER.exception('Could not read %s; starting from defaults', self._state_file)
            return
        self._count = count
        self._step = step

    def save(self):
        if not self._state_file:
            return
        count, step, _ = self.snapshot()
        tmp = self._state_file + '.tmp'
        with self._save_lock:
            try:
                directory = os.path.dirname(self._state_file)
                if directory:
                    os.makedirs(directory, exist_ok=True)
                with open(tmp, 'w') as f:
                    json.dump({'count': count, 'step': step}, f)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp, self._state_file)
            except OSError:
                LOGGER.exception('Could not save %s', self._state_file)

    def _notify(self):
        if self._on_change is None:
            return
        try:
            self._on_change()
        except Exception:
            LOGGER.exception('on_change callback failed')

    # ---- operations --------------------------------------------------
    def tick(self):
        """Advance by 1 if running. Returns True if a tick was applied."""
        with self._lock:
            if not self._running:
                return False
            self._count = _clamp(self._count + 1, INT32_MIN, INT32_MAX)
        self._notify()
        return True

    def start(self):
        with self._lock:
            self._running = True
        self._notify()

    def stop(self):
        with self._lock:
            self._running = False
        self.save()
        self._notify()

    def increment(self):
        with self._lock:
            self._count = _clamp(self._count + self._step, INT32_MIN, INT32_MAX)
        self.save()
        self._notify()

    def decrement(self):
        with self._lock:
            self._count = _clamp(self._count - self._step, INT32_MIN, INT32_MAX)
        self.save()
        self._notify()

    def set_step(self, value):
        """Set the step size. Raises ValueError unless it is an integer in 1..18000."""
        try:
            as_float = float(value)
            step = int(as_float)
        except (TypeError, ValueError, OverflowError):
            raise ValueError('step size must be a number, got %r' % (value,))
        if step != as_float:
            raise ValueError('step size must be a whole number, got %r' % (value,))
        if not STEP_MIN <= step <= STEP_MAX:
            raise ValueError('step size must be between %d and %d, got %d' % (STEP_MIN, STEP_MAX, step))
        with self._lock:
            self._step = step
        self.save()
        self._notify()

    # ---- background thread -------------------------------------------
    def begin(self):
        """Start the ticker thread (if needed) and start counting immediately."""
        with self._lock:
            if self._thread is None or not self._thread.is_alive():
                self._stop_evt.clear()
                self._thread = threading.Thread(target=self._loop, name='counter-tick', daemon=True)
                self._thread.start()
        self.start()

    def _loop(self):
        next_t = time.monotonic() + self._interval
        last_save = time.monotonic()
        while not self._stop_evt.wait(max(0.0, next_t - time.monotonic())):
            now = time.monotonic()
            next_t += self._interval
            if next_t <= now:  # fell behind; do not burst to catch up
                next_t = now + self._interval
            try:
                self.tick()
                if now - last_save >= self._save_every:
                    self.save()
                    last_save = now
            except Exception:
                LOGGER.exception('tick failed')

    def shutdown(self):
        """Stop the thread, mark stopped, and persist."""
        self._stop_evt.set()
        thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=3.0)
        with self._lock:
            self._running = False
        self.save()
        self._notify()
