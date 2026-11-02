"""Bounded deployment polling; lag blocks acceptance rather than failing the app."""
import time


def poll_revision(read_snapshot, expected, timeout=600, interval=15,
                  clock=time.monotonic, pause=time.sleep, record=lambda value: None):
    started = clock()
    attempts = []
    while True:
        attempt = {'attempt': len(attempts) + 1, 'elapsed_seconds': round(clock()-started, 2)}
        try:
            snapshot = read_snapshot()
            attempt['snapshot'] = snapshot
            ready = snapshot.get('git_commit') == expected and snapshot.get('git_tracked_changes') is False
        except Exception as exc:
            attempt['error'] = type(exc).__name__ + ': ' + str(exc)
            ready = False
        attempts.append(attempt)
        result = {'ready': ready, 'expected_commit': expected, 'attempts': attempts,
                  'elapsed_seconds': round(clock()-started, 2)}
        record(result)
        if ready or clock()-started >= timeout:
            return result
        pause(min(interval, max(0, timeout-(clock()-started))))
