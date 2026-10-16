#!/usr/bin/env python3
"""
Bounded unattended supervisor for the GD Bible Research Engine.

Runs successive *verified* batches of ``gd_research_pipeline.py`` until either
the eligible work is finished or a wall-clock budget expires.  It adds
orchestration only -- selection, checkpointing, provenance, escalation policy
and safety ceilings all remain in the pipeline, unchanged.

    ./gd_research_supervise.py start  --hours 24    # detached, survives DSH
    ./gd_research_supervise.py run    --hours 24    # same loop in the foreground
    ./gd_research_supervise.py status               # progress, no inference
    ./gd_research_supervise.py stop                 # graceful, after this batch

Each batch is a separate child process, so a crash costs at most the chunk in
flight: the next batch resumes from the findings on disk.  The supervisor
never exceeds ``BULK_CEILING`` model calls in a single run and never repeats
completed inference -- it stops with "no-progress" rather than spinning if a
batch somehow completes nothing.

Local inference only.  Cloud-tagged models are refused in the pipeline, and
the Ollama endpoint is a compile-time constant that no environment variable
can redirect.
"""

import argparse
import errno
import json
import os
import signal
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import gd_research_pipeline as pipeline  # noqa: E402  (reuse, do not duplicate)

PIPELINE_PATH = os.path.join(HERE, "gd_research_pipeline.py")
ARCHIVE = "/home/liongateos/PCOG-Research-Archive"
DEFAULT_ROOT = os.path.join(ARCHIVE, "research", "production")

# The per-run ceiling lives in the pipeline; we only mirror it for planning.
BULK_CEILING = pipeline.BULK_CEILING
MAX_BATCH = BULK_CEILING // 2          # 200 passages -> 400 calls, <= 450
DEFAULT_BATCH = 200
DEFAULT_BATCH_TIMEOUT = 3600           # generous: a 200-passage batch takes ~27 min


class SupervisorError(Exception):
    """Fatal supervisor condition -- stop rather than continue."""


# --------------------------------------------------------------------------
# paths
# --------------------------------------------------------------------------
def supervisor_dir(root):
    return os.path.join(root, "supervisor")


def pid_path(root):
    return os.path.join(supervisor_dir(root), "supervisor.pid")


def stop_path(root):
    return os.path.join(supervisor_dir(root), "STOP")


def history_path(root):
    return os.path.join(supervisor_dir(root), "run_history.jsonl")


def progress_path(root):
    return os.path.join(supervisor_dir(root), "progress.json")


def supervisor_log_path(root):
    return os.path.join(supervisor_dir(root), "supervisor.log")


def batch_log_path(root, stamp):
    return os.path.join(root, "logs", "batch-%s.log" % stamp)


def ensure_dirs(root):
    for path in (supervisor_dir(root), os.path.join(root, "logs"),
                 os.path.join(root, "findings"), os.path.join(root, "state")):
        os.makedirs(path, exist_ok=True)


# --------------------------------------------------------------------------
# planning -- pure, unit-testable, no inference
# --------------------------------------------------------------------------
def stage_batch_limit(stage):
    """Largest safe passage batch for one pipeline stage."""
    if stage not in ("screen", "escalate", "both"):
        raise SupervisorError("invalid stage: %s" % stage)
    return BULK_CEILING if stage in ("screen", "escalate") else MAX_BATCH


def resolve_batch_size(pending, requested=DEFAULT_BATCH, stage="both"):
    """Clamp one batch to eligible work and the stage's model-call ceiling."""
    if requested < 1:
        raise SupervisorError("batch size must be at least 1")
    limit = stage_batch_limit(stage)
    if requested > limit:
        raise SupervisorError(
            "batch size %d exceeds the safe %s-stage batch of %d "
            "(%d model calls per run)" % (requested, stage, limit, BULK_CEILING))
    return max(1, min(requested, pending))


def build_batch_argv(root, size, index=None, timeout=300, attempts=2,
                     stage="both"):
    """Build one bounded pipeline invocation for the requested stage."""
    limit = stage_batch_limit(stage)
    if size < 1 or size > limit:
        raise SupervisorError(
            "refusing unsafe %s-stage batch size: %d" % (stage, size))
    calls = min(size * (2 if stage == "both" else 1), BULK_CEILING)
    return [
        sys.executable, "-u", PIPELINE_PATH,
        "--stage", stage,
        "--limit", str(size),
        "--max-chunks", str(calls),
        "--timeout", str(timeout),
        "--attempts", str(attempts),
        "--index", index or pipeline.INDEX_PATH,
        "--output-root", root,
    ]


def pending_now(root, index=None, stage="both"):
    """Reuse the pipeline's stage-aware accounting."""
    status = pipeline.scan_findings(os.path.join(root, "findings"))
    return pipeline.pending_report(index or pipeline.INDEX_PATH, None, status,
                                   stage, pipeline.MODEL_OPTIONS)


def audit_queue_depth(root):
    try:
        return len(pipeline.load_audit_queue(
            os.path.join(root, "state", "zero_finding_queue.jsonl")))
    except Exception:  # noqa: BLE001 - progress reporting must never be fatal
        return 0


# --------------------------------------------------------------------------
# run history
# --------------------------------------------------------------------------
def append_history(root, record):
    ensure_dirs(root)
    path = history_path(root)
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def write_progress(root, snapshot):
    ensure_dirs(root)
    tmp = progress_path(root) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(snapshot, handle, indent=2, sort_keys=True)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, progress_path(root))


# --------------------------------------------------------------------------
# the loop
# --------------------------------------------------------------------------
def supervise(root, hours, batch=DEFAULT_BATCH, max_batches=None,
              batch_timeout=DEFAULT_BATCH_TIMEOUT, runner=None,
              clock=time.time, log=print, index=None, clear_stop=False,
              stage="both"):
    """Run batches until the work finishes, the budget expires, or we must stop.

    ``runner`` is injected so orchestration is testable without inference.
    Returns a short reason string.

    A STOP flag left by an earlier ``stop`` is honoured, not silently cleared:
    an unattended window must never start against an outstanding stop request.
    Pass ``clear_stop=True`` to begin a deliberately fresh window.
    """
    ensure_dirs(root)
    stage_batch_limit(stage)
    runner = runner or (lambda argv, timeout, logf: _run_batch(
        argv, timeout, logf, log))
    stop_file = stop_path(root)
    if clear_stop and os.path.exists(stop_file):
        os.remove(stop_file)
        log("[supervisor] cleared a previous STOP request (--clear-stop)")

    state = {"stop_requested": False}

    def request_stop(signum, _frame):
        state["stop_requested"] = True
        log("[supervisor] signal %d received -- will stop after this batch"
            % signum)

    previous = {}
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            previous[sig] = signal.signal(sig, request_stop)
        except (ValueError, OSError):  # not on the main thread
            pass

    started = clock()
    deadline = started + max(0.0, hours) * 3600.0
    batch_no = 0
    report = None          # bound before `finish` can close over it

    def finish(reason, report=None):
        for sig, handler in previous.items():
            try:
                signal.signal(sig, handler)
            except (ValueError, OSError):
                pass
        snapshot = {
            "reason": reason,
            "started_at": _iso(started),
            "finished_at": _iso(clock()),
            "wall_seconds": round(clock() - started, 1),
            "hours_budget": hours,
            "batches_completed": batch_no,
            "batch_size": batch,
            "stage": stage,
            "pending": (report or {}).get("pending"),
            "screened": (report or {}).get("screened"),
            "escalated": (report or {}).get("escalated"),
            "audit_queue": audit_queue_depth(root),
            "output_root": root,
        }
        write_progress(root, snapshot)
        log("\n[supervisor] finished: %s after %d batch(es), %.1f min"
            % (reason, batch_no, snapshot["wall_seconds"] / 60.0))
        return reason

    log("[supervisor] window %.2f h | stage %s | batch %d | ceiling %d calls/run | root %s"
        % (hours, stage, batch, BULK_CEILING, root))

    while True:
        if state["stop_requested"] or os.path.exists(stop_file):
            return finish("stop-requested", report)
        if clock() >= deadline:
            return finish("time-limit", report)
        if max_batches is not None and batch_no >= max_batches:
            return finish("max-batches", report)

        try:
            report = pending_now(root, index=index, stage=stage)
        except Exception as exc:  # noqa: BLE001 - unreadable index/state is fatal
            raise SupervisorError("cannot read pending work: %s" % exc)

        if report["pending"] <= 0:
            return finish("work-complete", report)

        size = resolve_batch_size(report["pending"], batch, stage=stage)
        remaining = deadline - clock()
        allowance = min(batch_timeout, max(1.0, remaining))
        stamp = time.strftime("%Y%m%d-%H%M%S")
        logfile = batch_log_path(root, stamp)

        log("\n[supervisor] batch %d: %d passages (pending %d, %.1f h left)"
            % (batch_no + 1, size, report["pending"], remaining / 3600.0))

        argv = build_batch_argv(root, size, index=index, stage=stage)
        began = clock()
        exit_code = runner(argv, allowance, logfile)
        elapsed = round(clock() - began, 1)

        after = pending_now(root, index=index, stage=stage)
        if stage == "screen":
            progressed = after["screened"] > report["screened"]
        elif stage == "escalate":
            progressed = after["escalated"] > report["escalated"]
        else:
            progressed = (
                after["screened"] > report["screened"]
                or after["escalated"] > report["escalated"]
            )

        append_history(root, {
            "batch": batch_no + 1,
            "started_at": _iso(began),
            "wall_seconds": elapsed,
            "exit_code": exit_code,
            "batch_size": size,
            "stage": stage,
            "pending_before": report["pending"],
            "pending_after": after["pending"],
            "screened_before": report["screened"],
            "screened_after": after["screened"],
            "escalated_before": report["escalated"],
            "escalated_after": after["escalated"],
            "progressed": progressed,
            "log": logfile,
        })

        if exit_code == 0 and not progressed:
            # Selection found work, the run reported success, yet nothing was
            # recorded.  Looping would burn the window for nothing.
            raise SupervisorError(
                "batch %d completed but recorded no new work (pending still %d); "
                "stopping instead of repeating completed inference"
                % (batch_no + 1, after["pending"]))

        if exit_code != 0:
            reason = _abort_reason(root)
            log("[supervisor] batch %d exited %d: %s"
                % (batch_no + 1, exit_code, reason or "unknown"))
            if _is_gpu_conflict(reason):
                return finish("gpu-conflict", after)
            consecutive = state.get("consecutive_failures", 0) + 1
            state["consecutive_failures"] = consecutive
            if consecutive >= 3:
                raise SupervisorError(
                    "3 consecutive failed batches (last: %s); stopping"
                    % (reason or "unknown"))
            log("[supervisor] retrying (consecutive failures: %d/3)" % consecutive)
            continue

        state["consecutive_failures"] = 0
        batch_no += 1
        report = after
        log("[supervisor] batch %d done in %.1f min; %d pending"
            % (batch_no, elapsed / 60.0, after["pending"]))


def _iso(epoch):
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(epoch))


def _abort_reason(root):
    try:
        with open(os.path.join(root, "state", "pipeline_state.json"),
                  encoding="utf-8") as handle:
            data = json.load(handle)
        return ((data.get("last_abort") or {}).get("reason")
                or (data.get("aborts") or [{}])[-1].get("reason"))
    except Exception:  # noqa: BLE001
        return None


def _is_gpu_conflict(reason):
    """A model we did not load occupying the GPU is never ours to evict."""
    if not reason:
        return False
    lowered = reason.lower()
    return "foreign" in lowered or "resident" in lowered


def _run_batch(argv, timeout, logfile, log):
    """Run one pipeline batch, teeing output to its own log (run history)."""
    os.makedirs(os.path.dirname(logfile), exist_ok=True)
    child_env = dict(os.environ)
    # The pipeline is local-only; make that explicit for the child too.
    child_env["OLLAMA_NO_CLOUD"] = "true"
    try:
        with open(logfile, "w", encoding="utf-8") as handle:
            proc = subprocess.Popen(argv, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, text=True,
                                    bufsize=1, env=child_env)
            try:
                for line in proc.stdout:
                    handle.write(line)
                    log("    " + line.rstrip())
                proc.wait(timeout=max(1, timeout))
            except subprocess.TimeoutExpired:
                log("[supervisor] batch exceeded its %.0fs allowance -- stopping it"
                    % timeout)
                proc.kill()
                proc.wait(timeout=60)
                handle.write("\n[supervisor] killed: exceeded batch allowance\n")
                return 124
            handle.flush()
            os.fsync(handle.fileno())
            return proc.returncode
    except OSError as exc:
        log("[supervisor] could not start the batch: %s" % exc)
        return 127


# --------------------------------------------------------------------------
# start / stop / status
# --------------------------------------------------------------------------
def read_pid(root):
    try:
        with open(pid_path(root), encoding="utf-8") as handle:
            return int(handle.read().strip())
    except (OSError, ValueError):
        return None


def pid_alive(pid):
    if not pid:
        return False
    try:
        os.kill(pid, 0)
    except OSError as exc:
        return exc.errno == errno.EPERM
    return True


def daemonize(root, argv, log_path):
    """Double-fork into a new session so the run survives DSH closing."""
    ensure_dirs(root)
    if os.fork() > 0:
        os._exit(0)
    os.setsid()
    if os.fork() > 0:
        os._exit(0)
    with open(log_path, "a", encoding="utf-8") as handle:
        os.dup2(handle.fileno(), sys.stdout.fileno())
        os.dup2(handle.fileno(), sys.stderr.fileno())
    devnull = os.open(os.devnull, os.O_RDONLY)
    os.dup2(devnull, sys.stdin.fileno())
    with open(pid_path(root), "w", encoding="utf-8") as handle:
        handle.write(str(os.getpid()) + "\n")
    log = lambda message: (print(message, flush=True))
    try:
        reason = supervise(root, **argv, log=log)
    except SupervisorError as exc:
        log("[supervisor] FATAL: %s" % exc)
        reason = "fatal"
    except Exception as exc:  # noqa: BLE001
        log("[supervisor] UNEXPECTED: %s: %s" % (type(exc).__name__, exc))
        reason = "error"
    finally:
        try:
            os.remove(pid_path(root))
        except OSError:
            pass
    log("[supervisor] exit: %s" % reason)
    os._exit(0 if reason in ("work-complete", "time-limit", "max-batches",
                             "stop-requested", "gpu-conflict") else 1)


def command_status(root, index=None):
    ensure_dirs(root)
    pid = read_pid(root)
    alive = pid_alive(pid)
    print("== GD Bible Research Engine -- unattended supervisor ==")
    print("  output root   : %s" % root)
    print("  state         : %s" % ("RUNNING (pid %d)" % pid if alive
                                    else "not running"))
    if os.path.exists(stop_path(root)):
        print("  STOP request  : present (will stop after the current batch)")

    try:
        snapshot = json.load(open(progress_path(root), encoding="utf-8"))
        print("  last window   : %s" % snapshot.get("reason"))
        print("  opened        : %s" % snapshot.get("started_at"))
        print("  batches done  : %s" % snapshot.get("batches_completed"))
        print("  wall          : %.1f min" % ((snapshot.get("wall_seconds") or 0) / 60.0))
    except (OSError, ValueError):
        print("  last window   : (no supervisor run recorded yet)")

    try:
        report = pending_now(root, index=index)
        done = report["high_total"] - report["pending"]
        pct = 100.0 * done / report["high_total"] if report["high_total"] else 0.0
        print()
        print("  HIGH passages : %d distinct" % report["high_total"])
        print("  completed     : %d (%.1f%%)" % (done, pct))
        print("  pending       : %d" % report["pending"])
        print("  escalated     : %d" % report["escalated"])
        print("  audit queue   : %d zero-finding passage(s)" % audit_queue_depth(root))
    except Exception as exc:  # noqa: BLE001
        print("  pending       : unavailable (%s)" % exc)

    try:
        with open(history_path(root), encoding="utf-8") as handle:
            rows = [json.loads(line) for line in handle if line.strip()]
        if rows:
            last = rows[-1]
            print()
            print("  batches run   : %d" % len(rows))
            print("  last batch    : #%s exit=%s %.1f min, %s new passages"
                  % (last.get("batch"), last.get("exit_code"),
                     (last.get("wall_seconds") or 0) / 60.0,
                     (last.get("screened_after", 0) - last.get("screened_before", 0))))
            print("  history       : %s" % history_path(root))
    except (OSError, ValueError):
        pass
    return 0


def command_stop(root):
    ensure_dirs(root)
    # The STOP file is authoritative: it works even if the pid is stale.
    with open(stop_path(root), "w", encoding="utf-8") as handle:
        handle.write("stop\n")
    pid = read_pid(root)
    if pid_alive(pid):
        print("asked supervisor (pid %d) to stop after the current batch" % pid)
    else:
        print("no supervisor running; the STOP flag stays set and a later "
              "start will refuse until you pass --clear-stop")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Bounded unattended supervisor for the GD Bible Research Engine.")
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p):
        p.add_argument("--hours", type=float, default=24.0,
                       help="wall-clock budget for this window (default 24)")
        p.add_argument("--batch", type=int, default=DEFAULT_BATCH,
                       help="passages per batch (stage-aware safety ceiling)")
        p.add_argument("--stage", choices=("screen", "escalate", "both"),
                       default="both",
                       help="pipeline phase to supervise (default both)")
        p.add_argument("--max-batches", type=int, default=None,
                       help="stop after this many batches (testing aid)")
        p.add_argument("--batch-timeout", type=int, default=DEFAULT_BATCH_TIMEOUT,
                       help="hard seconds allowed for one batch")
        p.add_argument("--output-root", default=DEFAULT_ROOT)
        p.add_argument("--index", default=pipeline.INDEX_PATH)
        p.add_argument("--clear-stop", dest="clear_stop", action="store_true",
                       default=False,
                       help="clear a STOP flag left by an earlier stop and "
                            "begin a fresh window")

    for name in ("run", "start"):
        p = sub.add_parser(name, help="%s the supervisor loop"
                           % ("detach and start" if name == "start" else "run"))
        common(p)

    for name in ("status", "stop"):
        p = sub.add_parser(name, help="%s (no inference)" % name)
        p.add_argument("--output-root", default=DEFAULT_ROOT)
        p.add_argument("--index", default=pipeline.INDEX_PATH)

    args = parser.parse_args(argv)
    root = os.path.abspath(args.output_root)

    if args.command == "status":
        return command_status(root, index=args.index)
    if args.command == "stop":
        return command_stop(root)

    stage_limit = stage_batch_limit(args.stage)
    if args.batch < 1 or args.batch > stage_limit:
        print("batch size must be between 1 and %d for stage %s"
              % (stage_limit, args.stage), file=sys.stderr)
        return 2

    options = dict(hours=args.hours, batch=args.batch, stage=args.stage,
                   max_batches=args.max_batches,
                   batch_timeout=args.batch_timeout, index=args.index,
                   clear_stop=args.clear_stop)

    if args.command == "start":
        if pid_alive(read_pid(root)):
            print("a supervisor is already running for %s" % root, file=sys.stderr)
            return 2
        print("starting detached supervisor for %s" % root)
        print("  log    : %s" % supervisor_log_path(root))
        print("  status : %s status" % os.path.basename(__file__))
        daemonize(root, options, supervisor_log_path(root))
        return 0

    try:
        reason = supervise(root, **options)
    except SupervisorError as exc:
        print("\n[supervisor] FATAL: %s" % exc, file=sys.stderr)
        return 1
    return 0 if reason in ("work-complete", "time-limit", "max-batches",
                           "stop-requested", "gpu-conflict") else 1


if __name__ == "__main__":
    raise SystemExit(main())
