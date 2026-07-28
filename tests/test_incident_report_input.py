from __future__ import annotations
import copy, importlib.util, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
VPATH=ROOT/"tools"/"python"/"validate_incident_report.py"
DPATH=ROOT/"reference_reports"/"incident_report"/"data"/"sql_server_2014_incident.json"
def validator():
    spec=importlib.util.spec_from_file_location("validator",VPATH); module=importlib.util.module_from_spec(spec)
    # Enregistré avant exec_module : @dataclass résout cls.__module__ via sys.modules (Python 3.12).
    sys.modules["validator"]=module; spec.loader.exec_module(module); return module
def data(): return json.loads(DPATH.read_text(encoding="utf-8-sig"))
def test_reference_input_is_valid(): assert validator().validate(data())==[]
def test_missing_title_is_reported():
    d=copy.deepcopy(data()); del d["findings"][0]["title"]
    assert "$.findings[0].title: required field missing" in [str(x) for x in validator().validate(d)]
def test_unknown_evidence_is_rejected():
    d=copy.deepcopy(data()); d["findings"][0]["evidence_ids"]=["missing"]
    assert any("unknown reference 'missing'" in str(x) for x in validator().validate(d))
def test_unknown_finding_is_rejected():
    d=copy.deepcopy(data()); d["recommendations"][0]["related_finding_ids"]=["missing"]
    assert any("unknown reference 'missing'" in str(x) for x in validator().validate(d))
def test_validator_does_not_depend_on_the_engine():
    """Dépendance commune limitée au noyau neutre : aucun cycle possible."""
    source=VPATH.read_text(encoding="utf-8")
    assert "adc_profile" in source
    assert "adc_engine" not in source

def test_summary_is_deterministic():
    v=validator(); d=data(); assert v.summary_blocks(d)==v.summary_blocks(copy.deepcopy(d))

def test_summary_follows_the_profile_order(tmp_path):
    """Le résumé n'a pas d'ordre propre : il suit le profil, seule source de l'ordre."""
    import yaml
    v=validator()
    reference=[component for component,_ in v.summary_blocks(data())]

    document=yaml.safe_load(Path(v.PROFILE_PATH).read_text(encoding="utf-8"))
    components=document["components"]
    positions={c.get("type"):i for i,c in enumerate(components)}
    left,right=positions["C-005-recommendation"],positions["C-006-risk"]
    components[left],components[right]=components[right],components[left]
    swapped=tmp_path/"profile.yaml"
    swapped.write_text(yaml.safe_dump(document,allow_unicode=True,sort_keys=False),encoding="utf-8")

    v.PROFILE_PATH=swapped
    modified=[component for component,_ in v.summary_blocks(data())]

    assert reference.index("C-005-recommendation")<reference.index("C-006-risk")
    assert modified.index("C-006-risk")<modified.index("C-005-recommendation")
    assert sorted(modified)==sorted(reference)
