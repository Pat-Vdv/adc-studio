#!/usr/bin/env python3
"""Validation structurelle d'une source de rapport d'incident.

Le résumé `--summary` n'a pas d'ordre propre : il affiche la résolution du
profil, seule description de l'ordre des blocs. Ce script ne dépend que du
noyau neutre `adc_profile`, jamais du moteur de composition.
"""
from __future__ import annotations
import argparse, json, sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from adc_profile import load_profile, resolve  # noqa: E402

SEVERITIES={"low","medium","high","critical"}
PRIORITIES=SEVERITIES

PROFILE_PATH = Path(__file__).resolve().parents[2] / "profiles" / "p-003-incident-report.yaml"

@dataclass(frozen=True)
class Issue:
    path:str
    message:str
    def __str__(self): return f"{self.path}: {self.message}"

def entries(data:Any,name:str,issues:list[Issue])->list[tuple[int,dict]]:
    """Occurrences exploitables d'une collection, les autres étant signalées.

    Le validateur ne redit pas ce que le schéma dit de la forme : il constate
    seulement qu'il ne peut pas raisonner sur une entrée mal formée, et le dit
    au lieu d'échouer. Une collection absente n'est pas une forme invalide.
    """
    raw=data.get(name)
    if raw is None: return []
    if not isinstance(raw,list):
        issues.append(Issue(f"$.{name}","malformed: list expected")); return []
    usable=[]
    for i,item in enumerate(raw):
        if isinstance(item,dict): usable.append((i,item))
        else: issues.append(Issue(f"$.{name}[{i}]","malformed: object expected"))
    return usable

def references(item:dict,field:str,path:str,issues:list[Issue])->list[tuple[int,str]]:
    """Références exploitables d'un champ, les autres étant signalées.

    Une chaîne se parcourrait caractère par caractère et produirait autant de
    références inconnues imaginaires : mieux vaut ne rien conclure. Une
    référence non textuelle n'est pas davantage confrontable à un index —
    cherchée dans un ensemble, une valeur non hachable lèverait.
    """
    raw=item.get(field)
    if raw is None: return []
    if not isinstance(raw,list):
        issues.append(Issue(f"{path}.{field}","malformed: list expected")); return []
    usable=[]
    for j,ref in enumerate(raw):
        if isinstance(ref,str): usable.append((j,ref))
        else: issues.append(Issue(f"{path}.{field}[{j}]","malformed: string expected"))
    return usable

def validate(data:Any)->list[Issue]:
    issues=[]
    if not isinstance(data,dict): return [Issue("$","malformed: object expected")]
    required=("schema_version","report","client","executive_summary","incident_context","environment","findings","recommendations","evidence","conclusion")
    for key in required:
        if key not in data: issues.append(Issue(f"$.{key}","required field missing"))
    if data.get("schema_version")!="1.0": issues.append(Issue("$.schema_version","expected '1.0'"))
    # Chaque collection n'est lue qu'une fois : une entrée mal formée doit être
    # signalée une fois, pas une fois par règle qui l'aurait parcourue.
    findings=entries(data,"findings",issues)
    recommendations=entries(data,"recommendations",issues)
    evidence=entries(data,"evidence",issues)
    risks=entries(data,"risks",issues)
    def ids(name,items):
        seen=set()
        for i,item in items:
            raw=item.get("id")
            # Un identifiant non textuel n'entre pas dans un index : non
            # hachable, il ferait lever l'appartenance à l'ensemble.
            if raw is not None and not isinstance(raw,str):
                issues.append(Issue(f"$.{name}[{i}].id","malformed: string expected")); continue
            if not raw:
                issues.append(Issue(f"$.{name}[{i}].id","required field missing")); continue
            if item["id"] in seen: issues.append(Issue(f"$.{name}[{i}].id",f"duplicate id '{item['id']}'"))
            seen.add(item["id"])
        return seen
    finding_ids=ids("findings",findings); recommendation_ids=ids("recommendations",recommendations); evidence_ids=ids("evidence",evidence)
    for i,item in findings:
        for field in ("id","title","severity","observation","impact","analysis","evidence_ids"):
            if field not in item: issues.append(Issue(f"$.findings[{i}].{field}","required field missing"))
        if item.get("severity") not in SEVERITIES: issues.append(Issue(f"$.findings[{i}].severity",f"expected one of {sorted(SEVERITIES)}"))
        for j,ref in references(item,"evidence_ids",f"$.findings[{i}]",issues):
            if ref not in evidence_ids: issues.append(Issue(f"$.findings[{i}].evidence_ids[{j}]",f"unknown reference '{ref}'"))
    for i,item in recommendations:
        for field in ("id","title","priority","description","rationale","related_finding_ids"):
            if field not in item: issues.append(Issue(f"$.recommendations[{i}].{field}","required field missing"))
        if item.get("priority") not in PRIORITIES: issues.append(Issue(f"$.recommendations[{i}].priority",f"expected one of {sorted(PRIORITIES)}"))
        for j,ref in references(item,"related_finding_ids",f"$.recommendations[{i}]",issues):
            if ref not in finding_ids: issues.append(Issue(f"$.recommendations[{i}].related_finding_ids[{j}]",f"unknown reference '{ref}'"))
    for i,item in risks:
        for j,ref in references(item,"mitigation_recommendation_ids",f"$.risks[{i}]",issues):
            if ref not in recommendation_ids: issues.append(Issue(f"$.risks[{i}].mitigation_recommendation_ids[{j}]",f"unknown reference '{ref}'"))
    return issues

def summary_blocks(data:dict[str,Any])->tuple[tuple[str,str],...]:
    """Occurrences ordonnées telles que le profil les déclare."""
    blocks,_=resolve(data,load_profile(PROFILE_PATH))
    return blocks

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
        for n,(component,instance) in enumerate(summary_blocks(data),1): print(f"{n:02d}. {component} :: {instance}")
    return 0
if __name__=="__main__": raise SystemExit(main())
