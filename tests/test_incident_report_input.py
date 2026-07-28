from __future__ import annotations
import copy, importlib.util, json, subprocess, sys
import pytest
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

# --- Robustesse : aucune exception observable -------------------------------
#
# Le validateur peut être appelé directement, sans qu'aucune validation de
# forme ne l'ait précédé. Il doit alors dire qu'il ne peut pas raisonner sur un
# noeud, jamais échouer. Il ne redit pas pour autant ce que le schéma dit :
# il ne conclut rien sur ce noeud, et poursuit sur les autres.

MALFORMED=(
    ("findings non-liste",          lambda d: d.update(findings="finding-001")),
    ("findings entier",             lambda d: d.update(findings=42)),
    ("findings objet",              lambda d: d.update(findings={"finding-001":{}})),
    ("findings[0] chaîne",          lambda d: d["findings"].__setitem__(0,"finding-001")),
    ("findings[0] liste",           lambda d: d["findings"].__setitem__(0,[])),
    ("recommendations[0] entier",   lambda d: d["recommendations"].__setitem__(0,42)),
    ("evidence non-liste",          lambda d: d.update(evidence={"e":{}})),
    ("risks non-liste",             lambda d: d.update(risks="aucun")),
    ("risks[0] chaîne",             lambda d: d.update(risks=["risk-001"])),
    ("evidence_ids chaîne",         lambda d: d["findings"][0].update(evidence_ids="evidence-001")),
    ("related_finding_ids entier",  lambda d: d["recommendations"][0].update(related_finding_ids=1)),
    ("mitigation_ids chaîne",       lambda d: d.update(risks=[{"id":"risk-001","mitigation_recommendation_ids":"recommendation-001"}])),
    ("source vide",                 lambda d: d.clear()),
)

@pytest.mark.parametrize("label,break_it",MALFORMED,ids=[label for label,_ in MALFORMED])
def test_a_malformed_source_is_diagnosed_never_raised(label,break_it):
    d=copy.deepcopy(data()); break_it(d)
    issues=validator().validate(d)  # ne doit lever aucune exception
    assert all(isinstance(str(issue),str) for issue in issues)

@pytest.mark.parametrize("value",["finding-001",[],42,None])
def test_a_malformed_entry_is_reported_once(value):
    d=copy.deepcopy(data()); d["findings"][0]=value
    malformed=[str(x) for x in validator().validate(d) if "malformed" in str(x)]
    assert malformed==["$.findings[0]: malformed: object expected"]

def test_business_rules_are_not_applied_to_a_malformed_entry():
    # Ni champs requis, ni vocabulaire : le validateur ne conclut rien sur une
    # entrée dont il ne peut pas lire la forme.
    d=copy.deepcopy(data()); d["findings"][0]="finding-001"
    paths=[x.path for x in validator().validate(d) if x.path.startswith("$.findings")]
    assert paths==["$.findings[0]"]

def test_a_malformed_entry_makes_the_references_that_cite_it_unresolvable():
    """Cascade assumée : le constat illisible n'entre pas dans l'index des
    identifiants, donc la recommandation qui le cite pointe réellement dans le
    vide. Ce second diagnostic n'est pas un doublon du premier, c'est sa
    conséquence — et il disparaîtra avec lui.
    """
    d=copy.deepcopy(data()); d["findings"][0]="finding-001"
    issues=[str(x) for x in validator().validate(d)]
    assert "$.findings[0]: malformed: object expected" in issues
    assert any("unknown reference 'finding-001'" in issue for issue in issues)

def test_a_malformed_reference_list_invents_no_reference():
    # Parcourue caractère par caractère, « evidence-001 » produirait douze
    # références inconnues imaginaires.
    d=copy.deepcopy(data()); d["findings"][0]["evidence_ids"]="evidence-001"
    issues=[str(x) for x in validator().validate(d)]
    assert issues==["$.findings[0].evidence_ids: malformed: list expected"]

def test_a_malformed_collection_does_not_stop_the_other_rules():
    # Un noeud illisible n'aveugle pas le validateur sur le reste de la source.
    d=copy.deepcopy(data()); d["risks"]="aucun"; d["recommendations"][0]["related_finding_ids"]=["missing"]
    issues=[str(x) for x in validator().validate(d)]
    assert "$.risks: malformed: list expected" in issues
    assert any("unknown reference 'missing'" in issue for issue in issues)

def test_a_source_that_is_not_an_object_is_diagnosed():
    assert [str(x) for x in validator().validate(["pas une source"])]==["$: malformed: object expected"]

# Valeurs choisies pour ce qu'elles cassent : non itérable, itérable de
# caractères, et surtout non hachable — une liste ou un objet cherché dans un
# index d'identifiants lèverait au lieu de répondre.
HOSTILE=(None,42,"x",True,0.5,[],{},[[]],[{"id":None}],{"a":1})

def _sweep():
    """Chaque noeud de la racine, puis chaque champ portant des références,
    remplacé par une valeur hostile."""
    for key in data():
        for value in HOSTILE: yield f"$.{key}={value!r}",(key,),value
    for path in (("findings",0,"id"),("findings",0,"evidence_ids"),
                 ("recommendations",0,"related_finding_ids"),("risks",0,"mitigation_recommendation_ids")):
        for value in HOSTILE: yield f"$.{'.'.join(map(str,path))}={value!r}",path,value

SWEEP=tuple(_sweep())

@pytest.mark.parametrize("label,path,value",SWEEP,ids=[label for label,_,_ in SWEEP])
def test_no_hostile_value_raises(label,path,value):
    """Balayage : aucune valeur ne doit produire d'exception observable.

    Les cas nommés plus haut documentent des comportements ; celui-ci couvre.
    Il a trouvé neuf exceptions qu'ils manquaient, toutes dues à des valeurs
    non hachables confrontées à un index d'identifiants.
    """
    d=copy.deepcopy(data())
    node=d
    for key in path[:-1]:
        node=node[key]
    node[path[-1]]=value
    for issue in validator().validate(d):  # ne doit lever aucune exception
        assert isinstance(str(issue),str)

@pytest.mark.parametrize("source",[None,42,"x",[],[1,2],{"":None},{"findings":[[]]}])
def test_no_hostile_source_raises(source):
    for issue in validator().validate(source):
        assert isinstance(str(issue),str)


def test_validator_does_not_depend_on_the_engine():
    """Contrôle statique : le source ne mentionne que le noyau neutre."""
    source=VPATH.read_text(encoding="utf-8")
    assert "adc_profile" in source
    assert "adc_engine" not in source

def test_validator_loads_no_engine_module():
    """Contrôle dynamique : aucun module du moteur chargé, fût-ce indirectement.

    Le contrôle statique ne verrait pas un import de commodité ajouté dans une
    dépendance du validateur ; celui-ci observe ce qui est réellement importé.
    """
    program=(
        "import importlib.util,sys;"
        f"sys.path.insert(0,{str(ROOT/'tools'/'python')!r});"
        f"spec=importlib.util.spec_from_file_location('v',{str(VPATH)!r});"
        "m=importlib.util.module_from_spec(spec);sys.modules['v']=m;spec.loader.exec_module(m);"
        "print(' '.join(sorted(n for n in sys.modules if n.startswith('adc_'))))"
    )
    result=subprocess.run([sys.executable,"-c",program],capture_output=True,text=True)
    assert result.returncode==0, result.stderr
    loaded=result.stdout.split()
    assert "adc_profile" in loaded  # le noyau neutre est bien chargé
    assert [name for name in loaded if not name.startswith("adc_profile")]==[]

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
