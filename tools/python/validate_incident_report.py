#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SEVERITIES={"low","medium","high","critical"}
PRIORITIES=SEVERITIES

@dataclass(frozen=True)
class Issue:
    path:str
    message:str
    def __str__(self): return f"{self.path}: {self.message}"

def validate(data:Any)->list[Issue]:
    issues=[]
    if not isinstance(data,dict): return [Issue("$","expected object")]
    required=("schema_version","report","client","executive_summary","incident_context","environment","findings","recommendations","evidence","conclusion")
    for key in required:
        if key not in data: issues.append(Issue(f"$.{key}","required field missing"))
    if data.get("schema_version")!="1.0": issues.append(Issue("$.schema_version","expected '1.0'"))
    def ids(name):
        seen=set()
        for i,item in enumerate(data.get(name,[])):
            if not isinstance(item,dict) or not item.get("id"):
                issues.append(Issue(f"$.{name}[{i}].id","required field missing")); continue
            if item["id"] in seen: issues.append(Issue(f"$.{name}[{i}].id",f"duplicate id '{item['id']}'"))
            seen.add(item["id"])
        return seen
    finding_ids=ids("findings"); recommendation_ids=ids("recommendations"); evidence_ids=ids("evidence")
    for i,item in enumerate(data.get("findings",[])):
        for field in ("id","title","severity","observation","impact","analysis","evidence_ids"):
            if field not in item: issues.append(Issue(f"$.findings[{i}].{field}","required field missing"))
        if item.get("severity") not in SEVERITIES: issues.append(Issue(f"$.findings[{i}].severity",f"expected one of {sorted(SEVERITIES)}"))
        for j,ref in enumerate(item.get("evidence_ids",[])):
            if ref not in evidence_ids: issues.append(Issue(f"$.findings[{i}].evidence_ids[{j}]",f"unknown reference '{ref}'"))
    for i,item in enumerate(data.get("recommendations",[])):
        for field in ("id","title","priority","description","rationale","related_finding_ids"):
            if field not in item: issues.append(Issue(f"$.recommendations[{i}].{field}","required field missing"))
        if item.get("priority") not in PRIORITIES: issues.append(Issue(f"$.recommendations[{i}].priority",f"expected one of {sorted(PRIORITIES)}"))
        for j,ref in enumerate(item.get("related_finding_ids",[])):
            if ref not in finding_ids: issues.append(Issue(f"$.recommendations[{i}].related_finding_ids[{j}]",f"unknown reference '{ref}'"))
    for i,item in enumerate(data.get("risks",[])):
        for j,ref in enumerate(item.get("mitigation_recommendation_ids",[])):
            if ref not in recommendation_ids: issues.append(Issue(f"$.risks[{i}].mitigation_recommendation_ids[{j}]",f"unknown reference '{ref}'"))
    return issues

def compose_block_index(data:dict[str,Any])->tuple[tuple[str,str],...]:
    blocks=[("C-001-cover","cover"),("C-002-identity-page","identity"),("C-003-executive-summary","executive-summary"),("narrative","incident-context"),("C-009-environment","environment")]
    if data.get("timeline"): blocks.append(("C-008-timeline","timeline"))
    blocks += [("narrative-investigation",x["id"]) for x in data.get("investigations",[])]
    blocks += [("C-004-finding",x["id"]) for x in data.get("findings",[])]
    if data.get("probable_cause"): blocks.append(("narrative","probable-cause"))
    blocks += [("C-007-decision",x["id"]) for x in data.get("actions_taken",[])]
    blocks += [("C-005-recommendation",x["id"]) for x in data.get("recommendations",[])]
    blocks += [("C-006-risk",x["id"]) for x in data.get("risks",[])]
    blocks.append(("narrative","conclusion"))
    blocks += [("C-010-evidence",x["id"]) for x in data.get("evidence",[])]
    return tuple(blocks)

def main():
    p=argparse.ArgumentParser(); p.add_argument("input",type=Path); p.add_argument("--summary",action="store_true"); a=p.parse_args()
    try: data=json.loads(a.input.read_text(encoding="utf-8-sig"))
    except Exception as exc: print(f"INVALID JSON: {exc}",file=sys.stderr); return 1
    issues=validate(data)
    if issues:
        print(f"INVALID: {len(issues)} issue(s).",file=sys.stderr)
        for issue in issues: print(f"- {issue}",file=sys.stderr)
        return 1
    print("VALID: incident report source is structurally consistent.")
    if a.summary:
        for n,(component,instance) in enumerate(compose_block_index(data),1): print(f"{n:02d}. {component} :: {instance}")
    return 0
if __name__=="__main__": raise SystemExit(main())
