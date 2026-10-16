#!/usr/bin/env python3
"""GD-M06-A1 resumable Stage A gate -> expansion enrichment runner."""
from __future__ import annotations
import argparse, hashlib, json, os, sys, time
from datetime import datetime, timezone
from pathlib import Path
import gd_research_model as mc

ROOT=Path(__file__).resolve().parent
# GD_PILOT_RUNS_ROOT: read-only input pilot_runs directory (never written).
# Production: /home/liongateos/pcog-archive-collector/pilot_runs
# Default: ROOT/pilot_runs (original sibling location).
_PILOT_RUNS=Path(os.environ.get("GD_PILOT_RUNS_ROOT",str(ROOT/"pilot_runs")))
STAGE=_PILOT_RUNS/"gd_m06_a1/stage_a/gd_m06_a1_stage_a_input.jsonl"
EXP=_PILOT_RUNS/"gd_m06_a1/expansion/gd_m06_a1_expansion_input.jsonl"
# GD_M06_OUTPUT_ROOT: root for all run outputs. Separated from read-only inputs.
# Must not be inside pcog-archive-collector, PCOG-Research-Archive,
# LionGateOS-Bible, ~/.dsh, case-study-editor-e1, or the input pilot_runs tree.
# Default: /home/liongateos/gd-m06-a1-runs
_OUTPUT_ROOT=Path(os.environ.get("GD_M06_OUTPUT_ROOT","/home/liongateos/gd-m06-a1-runs"))
RUN=_OUTPUT_ROOT/"overnight_v1"
# Trees outputs must never enter; enforced by check_out() before any write.
_FORBIDDEN_OUT=(
    Path("/home/liongateos/pcog-archive-collector"),
    Path("/home/liongateos/PCOG-Research-Archive"),
    Path("/home/liongateos/LionGateOS-Bible"),
    Path(os.path.expanduser("~/.dsh")),
    Path("/home/liongateos/case-study-editor-e1"),
    _PILOT_RUNS,
)
EXP_SHA="6569f2c87c9584c29cebf5260080ad578e52e39c4dc12ac61df36e076642e3d8"
REQ=("finding_uid quote_echo topic research_observation translation_relevance "
"translation_issue_type word_or_phrase_under_review scripture_refs_raw "
"scripture_refs_normalized scripture_ref_confidence doctrinal_or_contextual_theme "
"terminology_note wording_note capitalization_note evidence_summary evidence_strength "
"requires_original_language_check requires_human_review human_review_priority "
"quote_verification verification_status risk_flags model_identity generation_timestamp").split()
ENUM={
"translation_relevance":set("none low medium high".split()),
"translation_issue_type":set("scripture_reference translation terminology wording capitalization context doctrine none other".split()),
"scripture_ref_confidence":set("none low medium high".split()),
"evidence_strength":set("weak moderate strong".split()),
"human_review_priority":set("none low medium high".split()),
"quote_verification":set("valid mismatch out_of_bounds unknown".split()),
"verification_status":set("model_observation_unverified rejected_weak_evidence needs_human_review".split()),
}

def now(): return datetime.now(timezone.utc).isoformat()
def sha(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for b in iter(lambda:f.read(1<<20),b""): h.update(b)
    return h.hexdigest()
def rows(p):
    return [json.loads(x) for x in Path(p).read_text().splitlines() if x.strip()]
def atomic(p,s):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    t=p.with_suffix(p.suffix+".tmp"); t.write_text(s); os.replace(t,p)
def check_out(p):
    """Validate p is under _OUTPUT_ROOT and outside all forbidden trees.
    Resolves symlinks to detect escapes. Raises SystemExit. Never creates directories."""
    pa=Path(p).absolute(); pr=pa.resolve()
    oa=_OUTPUT_ROOT.absolute()
    try: pa.relative_to(oa)
    except ValueError: raise SystemExit(f"ABORT: output path not under approved root {oa}: {pa}")
    try: pr.relative_to(oa.resolve())
    except ValueError: raise SystemExit(f"ABORT: output path resolves outside approved root (symlink?): {pr}")
    for fb in _FORBIDDEN_OUT:
        fra=fb.resolve() if fb.exists() else Path(os.path.abspath(str(fb)))
        for cp in (pa,pr):
            try: cp.relative_to(fra)
            except ValueError: pass
            else: raise SystemExit(f"ABORT: output path inside forbidden tree {fb}")
def prompt(r, retry=""):
    base=f"""You are reviewing one GD Bible research finding.

Input record:
{json.dumps(r,ensure_ascii=False,sort_keys=True)}

Task:
Produce one JSON object for Bible translation research enrichment.

Required fields:
finding_uid, quote_echo, topic, research_observation, translation_relevance,
translation_issue_type, word_or_phrase_under_review, scripture_refs_raw,
scripture_refs_normalized, scripture_ref_confidence,
doctrinal_or_contextual_theme, terminology_note, wording_note,
capitalization_note, evidence_summary, evidence_strength,
requires_original_language_check, requires_human_review,
human_review_priority, quote_verification, verification_status,
risk_flags, model_identity, generation_timestamp.

Rules:
- Return JSON only.
- Preserve finding_uid exactly.
- Preserve quote exactly as quote_echo.
- scripture_refs_normalized must be an array.
- If anchor_verdict is mismatch or out_of_bounds, lower confidence and require human review.
- Do not make final Bible translation decisions."""
    if retry: base+="\n- Correct these prior validation errors: "+", ".join(retry)
    return base

def validate(o,r,model):
    e=[]
    if not isinstance(o,dict): return ["not_object"]
    e += ["missing:"+k for k in REQ if k not in o]
    if e: return e
    exact={"finding_uid":r["finding_uid"],"quote_echo":r.get("quote",""),
           "topic":r.get("topic"),"scripture_refs_raw":r.get("scripture_refs"),
           "quote_verification":r.get("anchor_verdict"),"model_identity":model}
    e += ["mismatch:"+k for k,v in exact.items() if o.get(k)!=v]
    e += ["bad_enum:"+k for k,v in ENUM.items() if o.get(k) not in v]
    if not isinstance(o.get("scripture_refs_normalized"),list): e.append("scripture_refs_normalized_not_array")
    if not isinstance(o.get("risk_flags"),list): e.append("risk_flags_not_array")
    if not isinstance(o.get("requires_original_language_check"),bool): e.append("original_language_check_not_bool")
    if not isinstance(o.get("requires_human_review"),bool): e.append("human_review_not_bool")
    if r.get("anchor_verdict") in {"mismatch","out_of_bounds"} and o.get("requires_human_review") is not True:
        e.append("invalid_anchor_requires_human_review")
    if not isinstance(o.get("generation_timestamp"),str) or not o["generation_timestamp"].strip():
        e.append("generation_timestamp_missing")
    return e

def path(run,uid): return run/"results"/f"{uid}.json"
def read_result(run,uid):
    p=path(run,uid)
    try: return json.loads(p.read_text()) if p.exists() else None
    except Exception: return None
def complete(run,r): return (read_result(run,r["finding_uid"]) or {}).get("status")=="ok"

def do_one(run,r,a):
    uid=r["finding_uid"]; errs=[]
    for n in range(1,a.validation_attempts+1):
        try:
            q=mc.generate_json(prompt(r,errs),a.model,base_url=a.base_url,
                options={"temperature":0,"num_ctx":8192},timeout=a.timeout,
                attempts=a.network_attempts,keep_alive=a.keep_alive)
            raw=q.get("response","")
            atomic(run/"raw"/f"{uid}.attempt{n}.txt",raw)
            try: o=json.loads(raw)
            except Exception as x: errs=["json:"+type(x).__name__]; continue
            errs=validate(o,r,a.model)
            if not errs:
                atomic(path(run,uid),json.dumps({"status":"ok","finding_uid":uid,
                    "input":r,"output":o,"model_meta":{k:v for k,v in q.items() if k!="response"},
                    "completed_at":now()},ensure_ascii=False,sort_keys=True,indent=2)+"\n")
                return True
        except Exception as x: errs=["model:"+type(x).__name__+":"+str(x)]
    atomic(path(run,uid),json.dumps({"status":"failed","finding_uid":uid,
        "input":r,"errors":errs,"failed_at":now()},ensure_ascii=False,sort_keys=True,indent=2)+"\n")
    return False

def report(run,stage,exp,phase):
    s=sum(complete(run,r) for r in stage); x=sum(complete(run,r) for r in exp)
    d={"updated_at":now(),"phase":phase,"stage_total":len(stage),"stage_ok":s,
       "expansion_total":len(exp),"all_ok":x,"additional_ok":max(0,x-s)}
    atomic(run/"status.json",json.dumps(d,indent=2,sort_keys=True)+"\n")
    return d

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--model",default="qwen3.6:27b"); ap.add_argument("--base-url",default=mc.DEFAULT_BASE_URL)
    ap.add_argument("--run-dir",default=str(RUN)); ap.add_argument("--hours",type=float,default=8.0)
    ap.add_argument("--timeout",type=int,default=600); ap.add_argument("--network-attempts",type=int,default=2)
    ap.add_argument("--validation-attempts",type=int,default=2); ap.add_argument("--keep-alive",default="30m")
    ap.add_argument("--dry-run",action="store_true"); a=ap.parse_args()
    check_out(_OUTPUT_ROOT/"_validate")  # validate output root before any file I/O
    if sha(EXP)!=EXP_SHA: raise SystemExit("ABORT: expansion queue SHA-256 mismatch")
    st,ex=rows(STAGE),rows(EXP)
    if len(st)!=397 or len(ex)!=19340: raise SystemExit("ABORT: frozen input count mismatch")
    by={r["finding_uid"]:r for r in ex}
    if any(by.get(r["finding_uid"])!=r for r in st): raise SystemExit("ABORT: Stage A not exact expansion subset")
    mc.assert_local_model(a.model)
    if a.dry_run:
        print("DRY_RUN: PASS"); print("stage_records:",len(st)); print("expansion_records:",len(ex))
        print("additional_after_gate:",len(ex)-len(st)); print("model_calls: 0"); print("NO_GPU_OR_MODEL_CALLS_MADE"); return 0
    run=Path(a.run_dir).resolve(); check_out(run)
    run.mkdir(parents=True,exist_ok=True)
    ident={"expansion_sha256":EXP_SHA,"stage_sha256":sha(STAGE),"runner_sha256":sha(Path(__file__)),"model":a.model}
    mp=run/"manifest.json"
    if mp.exists():
        old=json.loads(mp.read_text())
        if any(old.get(k)!=v for k,v in ident.items()): raise SystemExit("ABORT: resume identity mismatch")
    else: atomic(mp,json.dumps({**ident,"created_at":now(),"base_url":a.base_url},indent=2,sort_keys=True)+"\n")
    mc.check_competing_workloads(a.model,base_url=a.base_url,allow_evict=False)
    deadline=time.monotonic()+max(0,a.hours)*3600
    print("RUN_DIR:",run); print("PHASE: stage_a_gate")
    for i,r in enumerate(st,1):
        if complete(run,r): continue
        if time.monotonic()>=deadline: report(run,st,ex,"stage_a_time_limit"); print("TIME_LIMIT"); return 0
        print(f"STAGE {i}/{len(st)} {r['finding_uid']}",flush=True)
        if not do_one(run,r,a):
            report(run,st,ex,"stage_a_failed"); raise SystemExit("ABORT: Stage A validation failure; expansion not authorized")
    d=report(run,st,ex,"stage_a_passed")
    if d["stage_ok"]!=len(st): raise SystemExit("ABORT: Stage A gate incomplete")
    print("STAGE_A_GATE: PASS"); print("PHASE: expansion")
    stage_uids={r["finding_uid"] for r in st}
    todo=[r for r in ex if r["finding_uid"] not in stage_uids]
    for i,r in enumerate(todo,1):
        if complete(run,r): continue
        if time.monotonic()>=deadline: report(run,st,ex,"expansion_time_limit"); print("TIME_LIMIT"); return 0
        print(f"EXPANSION {i}/{len(todo)} {r['finding_uid']}",flush=True)
        if not do_one(run,r,a): print("WARNING: failed finding; continuing",flush=True)
        report(run,st,ex,"expansion")
    d=report(run,st,ex,"complete"); print("COMPLETE:",d); return 0
if __name__=="__main__": sys.exit(main())
