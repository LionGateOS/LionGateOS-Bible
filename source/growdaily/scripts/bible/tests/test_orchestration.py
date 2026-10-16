"""Orchestration tests for gd_research_supervise.py.

These exercise the supervisor only -- batch selection, checkpointing,
provenance and escalation stay in gd_research_pipeline.py and are covered by
test_milestone2.py.  The batch runner is injected, so nothing here performs
inference or touches Ollama.
"""

import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gd_research_pipeline as pipeline          # noqa: E402
import gd_research_supervise as sup             # noqa: E402

SCREEN = pipeline.SCREEN_MODEL
ESCALATE = pipeline.ESCALATE_MODEL


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def make_records(n, prefix="T"):
    records = []
    for i in range(n):
        records.append({
            "path": "documents/%s/doc%04d.doc" % (prefix, i),
            "collection": prefix,
            "priority": "high",
            "chunk_id": "c%04d" % i,
            "char_start": 0,
            "char_end": 100,
            "sha256": ("%064x" % (i + 1)),
            "score": 200 - i,
            "topics": ["translation"],
        })
    return records


def write_index(root, records):
    path = os.path.join(root, "index.jsonl")
    with open(path, "w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record) + "\n")
    return path


def findings_file(root, record):
    pipeline.FINDINGS_DIR = os.path.join(root, "findings")
    return pipeline.findings_path(record["path"], record["sha256"])


def screen_key(record):
    return pipeline.chunk_key(record["sha256"], record["chunk_id"], SCREEN,
                              pipeline.MODEL_OPTIONS)


def escalate_key(record):
    return pipeline.chunk_key(record["sha256"], record["chunk_id"], ESCALATE,
                              pipeline.MODEL_OPTIONS)


def is_done(root, record):
    target = findings_file(root, record)
    if not os.path.exists(target):
        return False
    with open(target, encoding="utf-8") as handle:
        document = json.load(handle)
    entry = (document.get("chunks") or {}).get(record["chunk_id"]) or {}
    screen = (entry.get("passes") or {}).get("screen") or {}
    return screen.get("key") == screen_key(record)


def mark_done(root, record, escalate=False, owed=False):
    """Write the findings entry the pipeline would leave behind.

    ``owed`` marks a screen pass that still needs its second pass (an
    unsupported quote), which is what keeps a chunk pending for escalation.
    """
    target = findings_file(root, record)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    document = {"schema_version": 1, "document": record["path"],
                "sha256": record["sha256"], "chunks": {}}
    if os.path.exists(target):
        with open(target, encoding="utf-8") as handle:
            document = json.load(handle)
    entry = document["chunks"].setdefault(record["chunk_id"],
                                          {"chunk_id": record["chunk_id"]})
    passes = entry.setdefault("passes", {})
    passes["screen"] = {
        "key": screen_key(record), "status": "ok", "json_parsed": True,
        "provenance": {"fabricated": 1 if owed else 0, "ambiguous": 0},
        "verified": [], "quarantined": [],
        "findings_total": 1 if owed else 0, "model": SCREEN,
    }
    if escalate:
        passes["escalate"] = {"key": escalate_key(record), "status": "ok"}
    with open(target, "w", encoding="utf-8") as handle:
        json.dump(document, handle)


def make_runner(records, status=0, progress=True):
    """A stand-in batch that completes the next *pending* records."""
    def runner(argv, timeout, logfile):
        if not progress:
            return status
        root = argv[argv.index("--output-root") + 1]
        size = int(argv[argv.index("--limit") + 1])
        done = [r for r in records if is_done(root, r)]
        for record in records[len(done):len(done) + size]:
            mark_done(root, record)
        return status
    return runner


class FakeClock(object):
    def __init__(self, start=1000.0):
        self.t = start

    def __call__(self):
        return self.t

    def advance(self, seconds):
        self.t += seconds


class SupervisorTestCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="gd-sup-")
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.records = make_records(12)
        self.index = write_index(self.root, self.records)

    def supervise(self, **kwargs):
        kwargs.setdefault("root", self.root)
        kwargs.setdefault("hours", 1.0)
        kwargs.setdefault("batch", 5)
        kwargs.setdefault("index", self.index)
        kwargs.setdefault("log", lambda *_a, **_k: None)
        return sup.supervise(**kwargs)

    def history(self):
        path = sup.history_path(self.root)
        if not os.path.exists(path):
            return []
        with open(path, encoding="utf-8") as handle:
            return [json.loads(line) for line in handle if line.strip()]


# --------------------------------------------------------------------------
# planning
# --------------------------------------------------------------------------
class TestBatchPlanning(unittest.TestCase):
    def test_clamps_to_pending(self):
        self.assertEqual(sup.resolve_batch_size(3, 200), 3)

    def test_uses_requested_when_work_allows(self):
        self.assertEqual(sup.resolve_batch_size(9999, 200), 200)

    def test_refuses_above_the_maximum_batch(self):
        with self.assertRaises(sup.SupervisorError):
            sup.resolve_batch_size(10 ** 6, sup.MAX_BATCH + 1)

    def test_refuses_non_positive_batch(self):
        with self.assertRaises(sup.SupervisorError):
            sup.resolve_batch_size(10, 0)

    def test_never_requests_more_than_the_ceiling(self):
        """No reachable batch size may exceed BULK_CEILING model calls."""
        for size in range(1, sup.MAX_BATCH + 1):
            argv = sup.build_batch_argv("/tmp/x", size)
            calls = int(argv[argv.index("--max-chunks") + 1])
            self.assertLessEqual(calls, sup.BULK_CEILING,
                                 "batch %d asked for %d calls" % (size, calls))

    def test_maximum_batch_uses_the_full_ceiling_but_not_more(self):
        argv = sup.build_batch_argv("/tmp/x", sup.MAX_BATCH)
        calls = int(argv[argv.index("--max-chunks") + 1])
        self.assertLessEqual(calls, sup.BULK_CEILING)

    def test_argv_refuses_an_unsafe_size(self):
        with self.assertRaises(sup.SupervisorError):
            sup.build_batch_argv("/tmp/x", sup.MAX_BATCH + 1)

    def test_argv_is_the_verified_two_pass_invocation(self):
        argv = sup.build_batch_argv("/root/out", 200)
        self.assertIn("--stage", argv)
        self.assertEqual(argv[argv.index("--stage") + 1], "both")
        self.assertEqual(argv[argv.index("--output-root") + 1], "/root/out")
        self.assertIn("gd_research_pipeline.py", " ".join(argv))

    def test_screen_stage_uses_one_call_per_passage(self):
        argv = sup.build_batch_argv("/root/out", 400, stage="screen")
        self.assertEqual(argv[argv.index("--stage") + 1], "screen")
        self.assertEqual(int(argv[argv.index("--max-chunks") + 1]), 400)

    def test_escalate_stage_uses_one_call_per_passage(self):
        argv = sup.build_batch_argv("/root/out", 400, stage="escalate")
        self.assertEqual(argv[argv.index("--stage") + 1], "escalate")
        self.assertEqual(int(argv[argv.index("--max-chunks") + 1]), 400)

    def test_both_stage_retains_two_pass_batch_limit(self):
        with self.assertRaises(sup.SupervisorError):
            sup.build_batch_argv("/root/out", sup.MAX_BATCH + 1, stage="both")

    def test_ceiling_is_read_from_the_pipeline(self):
        self.assertEqual(sup.BULK_CEILING, pipeline.BULK_CEILING)


# --------------------------------------------------------------------------
# the loop
# --------------------------------------------------------------------------
class TestSupervisorLoop(SupervisorTestCase):
    def test_stops_when_there_is_no_work(self):
        for record in self.records:
            mark_done(self.root, record)
        reason = self.supervise(runner=make_runner(self.records))
        self.assertEqual(reason, "work-complete")
        self.assertEqual(self.history(), [])

    def test_runs_a_batch_and_advances(self):
        reason = self.supervise(runner=make_runner(self.records), max_batches=1)
        self.assertEqual(reason, "max-batches")
        self.assertEqual(len(self.history()), 1)
        row = self.history()[0]
        self.assertEqual(row["exit_code"], 0)
        self.assertEqual(row["batch_size"], 5)
        self.assertEqual(row["screened_before"], 0)
        self.assertEqual(row["screened_after"], 5)
        self.assertTrue(row["progressed"])

    def test_successive_batches_take_new_passages(self):
        self.supervise(runner=make_runner(self.records), max_batches=2)
        rows = self.history()
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1]["screened_before"], 5)
        self.assertEqual(rows[1]["screened_after"], 10)
        self.assertEqual(rows[1]["screened_before"], rows[0]["screened_after"])

    def test_never_repeats_completed_inference(self):
        """A second window must pick up exactly where the first stopped."""
        self.supervise(runner=make_runner(self.records), max_batches=1)
        self.supervise(runner=make_runner(self.records), max_batches=1)
        rows = self.history()
        self.assertEqual(rows[1]["screened_before"], 5,
                         "second window redid work from the first")

    def test_resumes_pending_second_pass_work(self):
        """A screened-but-un-escalated chunk must still be eligible."""
        for record in self.records[:3]:
            mark_done(self.root, record, owed=True)   # screened, escalation owed
        for record in self.records[3:]:
            mark_done(self.root, record, escalate=True)

        report = sup.pending_now(self.root, index=self.index)
        self.assertEqual(report["screened"], 12)
        self.assertEqual(report["pending"], 3,
                         "chunks owing a second pass must remain pending")

    def test_escalate_stage_counts_second_pass_as_progress(self):
        for record in self.records[:3]:
            mark_done(self.root, record, owed=True)

        def runner(argv, timeout, logfile):
            self.assertEqual(argv[argv.index("--stage") + 1], "escalate")
            size = int(argv[argv.index("--limit") + 1])
            for record in self.records[:size]:
                mark_done(self.root, record, escalate=True)
            return 0

        reason = self.supervise(runner=runner, max_batches=1,
                                stage="escalate")
        self.assertEqual(reason, "max-batches")
        row = self.history()[0]
        self.assertEqual(row["screened_before"], row["screened_after"])
        self.assertEqual(row["escalated_before"], 0)
        self.assertEqual(row["escalated_after"], 3)
        self.assertTrue(row["progressed"])

    def test_stops_at_the_time_limit(self):
        clock = FakeClock()
        reason = self.supervise(runner=make_runner(self.records),
                                hours=0.0, clock=clock)
        self.assertEqual(reason, "time-limit")
        self.assertEqual(self.history(), [])

    def test_stops_when_the_budget_runs_out_mid_window(self):
        clock = FakeClock()

        def runner(argv, timeout, logfile):
            root = argv[argv.index("--output-root") + 1]
            size = int(argv[argv.index("--limit") + 1])
            done = [r for r in self.records if is_done(root, r)]
            for record in self.records[len(done):len(done) + size]:
                mark_done(root, record)
            clock.advance(0.6 * 3600)
            return 0

        reason = self.supervise(runner=runner, hours=1.0, clock=clock)
        self.assertEqual(reason, "time-limit")
        self.assertEqual(len(self.history()), 2)

    def test_respects_max_batches(self):
        reason = self.supervise(runner=make_runner(self.records), max_batches=3)
        self.assertEqual(reason, "max-batches")
        self.assertEqual(len(self.history()), 3)

    def test_stops_on_the_stop_flag(self):
        sup.ensure_dirs(self.root)
        with open(sup.stop_path(self.root), "w", encoding="utf-8") as handle:
            handle.write("stop\n")
        reason = self.supervise(runner=make_runner(self.records))
        self.assertEqual(reason, "stop-requested")
        self.assertEqual(self.history(), [])

    def test_batch_smaller_than_requested_when_little_work_remains(self):
        for record in self.records[:10]:
            mark_done(self.root, record)
        self.supervise(runner=make_runner(self.records), max_batches=1)
        self.assertEqual(self.history()[0]["batch_size"], 2)

    def test_records_no_progress_instead_of_looping(self):
        """A successful batch that records nothing must stop, not spin."""
        with self.assertRaises(sup.SupervisorError):
            self.supervise(runner=make_runner(self.records, progress=False))

    def test_stops_after_three_consecutive_failures(self):
        with self.assertRaises(sup.SupervisorError):
            self.supervise(runner=make_runner(self.records, status=1,
                                              progress=False))

    def test_retries_a_single_failure_then_succeeds(self):
        calls = {"n": 0}
        good = make_runner(self.records)

        def flaky(argv, timeout, logfile):
            calls["n"] += 1
            if calls["n"] == 1:
                return 1
            return good(argv, timeout, logfile)

        reason = self.supervise(runner=flaky, max_batches=1)
        self.assertEqual(reason, "max-batches")
        self.assertEqual(len(self.history()), 2)     # one failure + one success
        self.assertEqual(self.history()[0]["exit_code"], 1)

    def test_stops_on_a_gpu_conflict(self):
        def runner(argv, timeout, logfile):
            sup.ensure_dirs(self.root)
            with open(os.path.join(self.root, "state", "pipeline_state.json"),
                      "w", encoding="utf-8") as handle:
                json.dump({"last_abort": {
                    "reason": "model 'other-llm' is resident in VRAM but was "
                              "not loaded by this run"}}, handle)
            return 1

        reason = self.supervise(runner=runner)
        self.assertEqual(reason, "gpu-conflict")

    def test_writes_run_history_and_progress(self):
        self.supervise(runner=make_runner(self.records), max_batches=1)
        self.assertTrue(os.path.exists(sup.history_path(self.root)))
        with open(sup.progress_path(self.root), encoding="utf-8") as handle:
            snapshot = json.load(handle)
        self.assertEqual(snapshot["reason"], "max-batches")
        self.assertEqual(snapshot["batches_completed"], 1)
        self.assertEqual(snapshot["pending"], 7)

    def test_history_survives_across_windows(self):
        self.supervise(runner=make_runner(self.records), max_batches=1)
        self.supervise(runner=make_runner(self.records), max_batches=1)
        self.assertEqual(len(self.history()), 2)


# --------------------------------------------------------------------------
# gpu-conflict classification
# --------------------------------------------------------------------------
class TestGpuConflictDetection(unittest.TestCase):
    def test_recognises_a_foreign_resident_model(self):
        self.assertTrue(sup._is_gpu_conflict(
            "model 'llama3' is resident but was not loaded by this run"))

    def test_ignores_ordinary_errors(self):
        self.assertFalse(sup._is_gpu_conflict("connection refused"))
        self.assertFalse(sup._is_gpu_conflict(None))


# --------------------------------------------------------------------------
# commands
# --------------------------------------------------------------------------
class TestSupervisorCommands(SupervisorTestCase):
    def test_status_reports_progress_without_inference(self):
        mark_done(self.root, self.records[0])
        self.assertEqual(sup.command_status(self.root, index=self.index), 0)

    def test_status_counts_completed_work(self):
        for record in self.records[:4]:
            mark_done(self.root, record)
        report = sup.pending_now(self.root, index=self.index)
        self.assertEqual(report["screened"], 4)
        self.assertEqual(report["pending"], 8)
        self.assertEqual(report["high_total"], 12)

    def test_stop_creates_the_stop_flag(self):
        self.assertEqual(sup.command_stop(self.root), 0)
        self.assertTrue(os.path.exists(sup.stop_path(self.root)))

    def test_stop_is_honoured_even_with_a_stale_pid(self):
        sup.ensure_dirs(self.root)
        with open(sup.pid_path(self.root), "w", encoding="utf-8") as handle:
            handle.write("999999\n")
        self.assertEqual(sup.command_stop(self.root), 0)
        reason = self.supervise(runner=make_runner(self.records))
        self.assertEqual(reason, "stop-requested")

    def test_cli_rejects_an_oversized_batch(self):
        code = sup.main(["run", "--batch", str(sup.MAX_BATCH + 1),
                         "--output-root", self.root])
        self.assertEqual(code, 2)

    def test_cli_status_exits_zero(self):
        self.assertEqual(sup.main(["status", "--output-root", self.root,
                                   "--index", self.index]), 0)


if __name__ == "__main__":
    unittest.main()
