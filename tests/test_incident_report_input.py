from __future__ import annotations
import copy, importlib.util, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
VPATH=ROOT/"tools"/"python"/"validate_incident_report.py"
DPATH=ROOT/"reference_reports"/"incident_report"/"data"/"sql_server_2014_incident.json"
def validator():
    spec=importlib.util.spec_from_file_location("validator",VPATH); module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module
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
def test_composition_is_deterministic():
    v=validator(); d=data(); assert v.compose_block_index(d)==v.compose_block_index(copy.deepcopy(d))
