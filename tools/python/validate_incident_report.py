#!/usr/bin/env python3
"""Validation structurelle d'une source de rapport d'incident.

`validate` ne porte que des règles **métier** : références, unicité, présence,
vocabulaires. Elle ne redit pas ce que les contrats de composants disent de la
forme, et reste appelable seule — aucune validation de forme n'est supposée
l'avoir précédée, aucune entrée malformée ne la fait échouer.

La ligne de commande, elle, enchaîne les deux : forme d'abord, métier ensuite,
et présente les diagnostics ensemble sans les confondre. C'est ici, et non dans
`validate`, que les deux validations se rencontrent.

Le résumé `--summary` n'a pas d'ordre propre : il affiche la résolution du
profil, seule description de l'ordre des blocs. Ce script ne dépend que de
modules neutres, jamais du moteur de composition.
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import adc_contracts  # noqa: E402
from adc_diagnostics import BUSINESS, ValidationDiagnostic  # noqa: E402
from adc_profile import load_profile, resolve  # noqa: E402

PROFILE_PATH = Path(__file__).resolve().parents[2] / "profiles" / "p-003-incident-report.yaml"

# Vocabulaire des diagnostics métier. La forme a le sien — les mots-clés du
# schéma — et les deux n'ont pas à se ressembler.
MALFORMED="malformed"; MISSING="required_field_missing"; DUPLICATE="duplicate_id"
UNKNOWN_REFERENCE="unknown_reference"; UNEXPECTED="unexpected_value"

def issue(path:str,code:str,message:str)->ValidationDiagnostic:
    """Diagnostic métier : la source est en cause, aucun contrat nommé ne l'est."""
    return ValidationDiagnostic(path=path,message=message,source=BUSINESS,code=code)

def entries(data:Any,name:str,issues:list[ValidationDiagnostic])->list[tuple[int,dict]]:
    """Occurrences exploitables d'une collection, les autres étant signalées.

    Le validateur ne redit pas ce que le schéma dit de la forme : il constate
    seulement qu'il ne peut pas raisonner sur une entrée mal formée, et le dit
    au lieu d'échouer. Une collection absente n'est pas une forme invalide.
    """
    raw=data.get(name)
    if raw is None: return []
    if not isinstance(raw,list):
        issues.append(issue(f"$.{name}",MALFORMED,"malformed: list expected")); return []
    usable=[]
    for i,item in enumerate(raw):
        if isinstance(item,dict): usable.append((i,item))
        else: issues.append(issue(f"$.{name}[{i}]",MALFORMED,"malformed: object expected"))
    return usable

def node(data:Any,name:str,issues:list[ValidationDiagnostic])->dict|None:
    """Noeud exploitable d'un bloc unique, l'écart étant déclaré plutôt que tu.

    Pendant de `entries` pour un noeud qui n'est pas une collection : un noeud
    absent ne dit rien, un noeud mal formé n'est pas jugé — le validateur
    déclare seulement qu'aucune règle métier ne peut lui être appliquée.
    """
    raw=data.get(name)
    if raw is None: return None
    if not isinstance(raw,dict):
        issues.append(issue(f"$.{name}",MALFORMED,"malformed: object expected")); return None
    return raw

def references(item:dict,field:str,path:str,issues:list[ValidationDiagnostic])->list[tuple[int,str]]:
    """Références exploitables d'un champ, les autres étant signalées.

    Une chaîne se parcourrait caractère par caractère et produirait autant de
    références inconnues imaginaires : mieux vaut ne rien conclure. Une
    référence non textuelle n'est pas davantage confrontable à un index —
    cherchée dans un ensemble, une valeur non hachable lèverait.
    """
    raw=item.get(field)
    if raw is None: return []
    if not isinstance(raw,list):
        issues.append(issue(f"{path}.{field}",MALFORMED,"malformed: list expected")); return []
    usable=[]
    for j,ref in enumerate(raw):
        if isinstance(ref,str): usable.append((j,ref))
        else: issues.append(issue(f"{path}.{field}[{j}]",MALFORMED,"malformed: string expected"))
    return usable

def validate(data:Any)->list[ValidationDiagnostic]:
    """Règles métier d'une source de rapport d'incident.

    La forme locale — champs requis d'une occurrence, vocabulaires fermés,
    types — appartient aux contrats de composants et n'est pas revérifiée ici
    (ADR-0010). Ne subsistent que les règles qu'aucun schéma local ne peut
    voir : présence des noeuds de la famille, unicité des identifiants,
    résolubilité des références.

    Les diagnostics « malformed » ne sont pas une exception à ce partage : ils
    ne portent pas de verdict sur la forme, ils déclarent une abstention — le
    validateur ne peut pas appliquer une règle métier à ce noeud.
    """
    issues=[]
    if not isinstance(data,dict): return [issue("$",MALFORMED,"malformed: object expected")]
    required=("schema_version","report","client","executive_summary","incident_context","environment","findings","recommendations","evidence","conclusion")
    for key in required:
        if key not in data: issues.append(issue(f"$.{key}",MISSING,"required field missing"))
    if data.get("schema_version")!="1.0": issues.append(issue("$.schema_version",UNEXPECTED,"expected '1.0'"))
    # Chaque collection n'est lue qu'une fois : une entrée mal formée doit être
    # signalée une fois, pas une fois par règle qui l'aurait parcourue.
    findings=entries(data,"findings",issues)
    recommendations=entries(data,"recommendations",issues)
    evidence=entries(data,"evidence",issues)
    risks=entries(data,"risks",issues)
    decisions=entries(data,"actions_taken",issues)
    investigations=entries(data,"investigations",issues)
    def ids(name,items):
        seen=set()
        for i,item in items:
            raw=item.get("id")
            # Qu'un identifiant soit présent, textuel et non vide relève du
            # contrat du composant. Ici, un identifiant inexploitable est
            # seulement écarté de l'index — non hachable, il ferait d'ailleurs
            # lever l'appartenance à l'ensemble. Les références qui le visent
            # deviendront non résolues, ce qui est le vrai constat métier.
            if not isinstance(raw,str) or not raw: continue
            if raw in seen: issues.append(issue(f"$.{name}[{i}].id",DUPLICATE,f"duplicate id '{raw}'"))
            seen.add(raw)
        return seen
    finding_ids=ids("findings",findings); recommendation_ids=ids("recommendations",recommendations); evidence_ids=ids("evidence",evidence)
    # Les trois blocs répétables que personne ne référence. L'unicité n'y est
    # pas moins exigible : la résolution instancie **toute** occurrence par son
    # identifiant, et deux entrées qui le partagent composent deux fois la
    # première — la seconde disparaît du rapport sans diagnostic. L'unicité est
    # donc une propriété de l'identité d'occurrence, pas un service rendu aux
    # références ; l'index qu'elles produisent n'a ici aucun consommateur.
    ids("actions_taken",decisions); ids("risks",risks); ids("investigations",investigations)
    for i,item in findings:
        for j,ref in references(item,"evidence_ids",f"$.findings[{i}]",issues):
            if ref not in evidence_ids: issues.append(issue(f"$.findings[{i}].evidence_ids[{j}]",UNKNOWN_REFERENCE,f"unknown reference '{ref}'"))
    for i,item in recommendations:
        for j,ref in references(item,"related_finding_ids",f"$.recommendations[{i}]",issues):
            if ref not in finding_ids: issues.append(issue(f"$.recommendations[{i}].related_finding_ids[{j}]",UNKNOWN_REFERENCE,f"unknown reference '{ref}'"))
    for i,item in risks:
        for j,ref in references(item,"mitigation_recommendation_ids",f"$.risks[{i}]",issues):
            if ref not in recommendation_ids: issues.append(issue(f"$.risks[{i}].mitigation_recommendation_ids[{j}]",UNKNOWN_REFERENCE,f"unknown reference '{ref}'"))
    # `probable_cause` est un bloc unique, mais ses références sont des
    # références comme les autres : une cible inconnue est un défaut métier
    # (ADR-0009), quel que soit le statut contractuel du noeud qui la porte.
    probable_cause=node(data,"probable_cause",issues)
    if probable_cause is not None:
        for j,ref in references(probable_cause,"supporting_finding_ids","$.probable_cause",issues):
            if ref not in finding_ids: issues.append(issue(f"$.probable_cause.supporting_finding_ids[{j}]",UNKNOWN_REFERENCE,f"unknown reference '{ref}'"))
    return issues

def summary_blocks(data:dict[str,Any])->tuple[tuple[str,str],...]:
    """Occurrences ordonnées telles que le profil les déclare."""
    blocks,_=resolve(data,load_profile(PROFILE_PATH))
    return blocks

def main():
    p=argparse.ArgumentParser(); p.add_argument("input",type=Path); p.add_argument("--summary",action="store_true"); a=p.parse_args()
    try: data=json.loads(a.input.read_text(encoding="utf-8-sig"))
    except Exception as exc: print(f"INVALID JSON: {exc}",file=sys.stderr); return 1
    # Forme d'abord, métier ensuite. Les deux sont rapportées d'un coup : la
    # validation métier ne dépend pas de la première, un noeud illisible ne
    # l'empêche pas de conclure sur le reste.
    diagnostics=[*adc_contracts.report_diagnostics(data),*validate(data)]
    if diagnostics:
        print(f"INVALID: {len(diagnostics)} issue(s).",file=sys.stderr)
        for diagnostic in diagnostics: print(f"- {diagnostic}",file=sys.stderr)
        return 1
    print("VALID: incident report source is structurally consistent.")
    if a.summary:
        for n,(component,instance) in enumerate(summary_blocks(data),1): print(f"{n:02d}. {component} :: {instance}")
    return 0
if __name__=="__main__": raise SystemExit(main())
