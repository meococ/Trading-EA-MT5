"""heavy_run.py - the Owner's rule (LEAD_RULINGS R65): heavy jobs never run in parallel.

Usage (from the PA_Pro folder):
    python research/perception/tools/heavy_run.py --lane box-lab -- python -m evalcheck.some_run --all
    python research/perception/tools/heavy_run.py --status

What it does:
  1. Takes the one PA-PRO heavy lock (_scratch/heavy.lock). If another lane holds it, it waits and
     logs the wait; it gives up after --max-wait-min (exit code 75) so the lane can do light work first.
  2. Runs the command at BelowNormal priority with one thread per math library (no multi-core fan-out).
  3. Releases the lock when the command ends. The OS also frees it if this process dies, so a crashed
     lane never leaves a stale lock behind, and nothing has to be deleted.
Every step is logged to research/perception/tools/heavy_run.log with the system clock.
"""
import argparse
import datetime as _dt
import json
import os
import subprocess
import sys
import time

TOOLS = os.path.dirname(os.path.abspath(__file__))
PA_ROOT = os.path.abspath(os.path.join(TOOLS, '..', '..', '..'))
LOCK = os.path.join(PA_ROOT, '_scratch', 'heavy.lock')
HOLDER = os.path.join(PA_ROOT, '_scratch', 'heavy.holder.json')
LOG = os.path.join(TOOLS, 'heavy_run.log')
IS_WIN = os.name == 'nt'
ONE_THREAD = ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS',
              'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS', 'NUMBA_NUM_THREADS')

if IS_WIN:
    import msvcrt
else:
    import fcntl


def now():
    return _dt.datetime.now(_dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def log(msg):
    line = '%s %s\n' % (now(), msg)
    try:
        with open(LOG, 'a', encoding='utf-8') as f:
            f.write(line)
    except OSError:
        pass
    sys.stderr.write('[heavy_run] ' + line)


def try_lock(fd):
    try:
        os.lseek(fd, 0, os.SEEK_SET)
        if IS_WIN:
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        else:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except OSError:
        return False


def unlock(fd):
    try:
        os.lseek(fd, 0, os.SEEK_SET)
        if IS_WIN:
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        else:
            fcntl.flock(fd, fcntl.LOCK_UN)
    except OSError:
        pass


def open_lock():
    os.makedirs(os.path.dirname(LOCK), exist_ok=True)
    fd = os.open(LOCK, os.O_RDWR | os.O_CREAT)
    if os.fstat(fd).st_size == 0:
        os.write(fd, b'L')  # a byte to lock on Windows
    return fd


def read_holder():
    try:
        with open(HOLDER, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def status():
    fd = open_lock()
    free = try_lock(fd)
    if free:
        unlock(fd)
    os.close(fd)
    h = read_holder()
    print('heavy lock: %s' % ('FREE' if free else 'HELD'))
    if not free:
        print('holder: lane=%s pid=%s since=%s cmd=%s' % (h.get('lane'), h.get('pid'), h.get('since'), h.get('cmd')))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--lane', help='your lane name (build, box-lab, eval-audit, dr-box, ...)')
    ap.add_argument('--max-wait-min', type=float, default=180.0)
    ap.add_argument('--poll-s', type=float, default=20.0)
    ap.add_argument('--status', action='store_true')
    ap.add_argument('cmd', nargs=argparse.REMAINDER)
    a = ap.parse_args()
    if a.status:
        return status()
    cmd = a.cmd[1:] if a.cmd and a.cmd[0] == '--' else a.cmd
    if not a.lane or not cmd:
        ap.error('need --lane and a command after --')
    shown = ' '.join(cmd)[:200]

    fd = open_lock()
    t0 = time.time()
    waited = False
    while not try_lock(fd):
        if not waited:
            h = read_holder()
            log('WAIT lane=%s for holder lane=%s pid=%s since=%s' % (a.lane, h.get('lane'), h.get('pid'), h.get('since')))
            waited = True
        if time.time() - t0 > a.max_wait_min * 60:
            log('GAVE-UP lane=%s after %.0f min; do light work and retry' % (a.lane, a.max_wait_min))
            os.close(fd)
            return 75
        time.sleep(a.poll_s)

    info = {'lane': a.lane, 'pid': os.getpid(), 'since': now(), 'cmd': shown}
    try:
        with open(HOLDER, 'w', encoding='utf-8') as f:
            json.dump(info, f)
    except OSError:
        pass
    log('START lane=%s waited=%.1fmin cmd=%s' % (a.lane, (time.time() - t0) / 60.0, shown))

    env = dict(os.environ)
    for k in ONE_THREAD:
        env[k] = '1'
    kw = {'env': env}
    if IS_WIN:
        kw['creationflags'] = subprocess.BELOW_NORMAL_PRIORITY_CLASS
    t1 = time.time()
    rc = 1
    try:
        p = subprocess.Popen(cmd, **kw)
        if not IS_WIN:
            try:
                os.setpriority(os.PRIO_PROCESS, p.pid, 10)
            except (OSError, AttributeError):
                pass
        rc = p.wait()
    except KeyboardInterrupt:
        rc = 130
    except OSError as e:
        log('ERROR lane=%s could not start: %s' % (a.lane, e))
        rc = 127
    finally:
        log('END lane=%s rc=%s run=%.1fmin' % (a.lane, rc, (time.time() - t1) / 60.0))
        try:
            with open(HOLDER, 'w', encoding='utf-8') as f:
                json.dump({'lane': None, 'last': info, 'ended': now(), 'rc': rc}, f)
        except OSError:
            pass
        unlock(fd)
        os.close(fd)
    return rc


if __name__ == '__main__':
    sys.exit(main())
