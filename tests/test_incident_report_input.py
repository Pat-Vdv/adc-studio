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

# --- Partage avec les contrats de composants -------------------------------
#
# Les règles de forme ne sont plus vérifiées deux fois. Chaque cas ci-dessous
# le prouve des deux côtés : le validateur métier ne la porte plus, le contrat
# du composant la porte. Une règle qui disparaîtrait des deux fait échouer le
# test — c'est la seule garantie qu'elle a changé de responsable et non de vie.

TRANSFERRED=(
    ("constat sans titre",             lambda d: d["findings"][0].pop("title"),            "$.findings[0].title",            "C-004-finding",         "required"),
    ("constat sans identifiant",       lambda d: d["findings"][0].pop("id"),               "$.findings[0].id",               "C-004-finding",         "required"),
    ("gravité hors vocabulaire",       lambda d: d["findings"][0].update(severity="urgent"),"$.findings[0].severity",         "C-004-finding",         "enum"),
    ("recommandation sans rationale",  lambda d: d["recommendations"][0].pop("rationale"), "$.recommendations[0].rationale", "C-005-recommendation",  "required"),
    ("priorité hors vocabulaire",      lambda d: d["recommendations"][0].update(priority="P1"),"$.recommendations[0].priority","C-005-recommendation","enum"),
    ("preuve à identifiant vide",      lambda d: d["evidence"][0].update(id=""),           "$.evidence[0].id",               "C-010-evidence",        "minLength"),
    ("identifiant non textuel",        lambda d: d["findings"][0].update(id=42),           "$.findings[0].id",               "C-004-finding",         "type"),
)

@pytest.mark.parametrize("label,break_it,path,component,code",TRANSFERRED,ids=[c[0] for c in TRANSFERRED])
def test_a_form_rule_belongs_to_the_contract_alone(label,break_it,path,component,code):
    import adc_contracts
    d=copy.deepcopy(data()); break_it(d)
    business=[x for x in validator().validate(d) if x.path.startswith(path)]
    assert business==[], f"le validateur métier redit une règle de forme : {business}"
    contract=[x for x in adc_contracts.report_diagnostics(d) if x.component==component and x.code==code]
    assert contract, "la règle n'est portée par personne"

def test_the_reference_source_still_satisfies_both_validations():
    import adc_contracts
    assert validator().validate(data())==[]
    assert adc_contracts.report_diagnostics(data())==()
def test_unknown_evidence_is_rejected():
    d=copy.deepcopy(data()); d["findings"][0]["evidence_ids"]=["missing"]
    assert any("unknown reference 'missing'" in str(x) for x in validator().validate(d))
def test_unknown_finding_is_rejected():
    d=copy.deepcopy(data()); d["recommendations"][0]["related_finding_ids"]=["missing"]
    assert any("unknown reference 'missing'" in str(x) for x in validator().validate(d))
def test_unknown_supporting_finding_is_rejected():
    # Une référence portée par un bloc unique reste une référence : son
    # contrôle appartient au métier, pas à la composition qui la signalait
    # seule jusqu'ici.
    d=copy.deepcopy(data()); d["probable_cause"]["supporting_finding_ids"]=["missing"]
    issues=validator().validate(d)
    assert [str(x) for x in issues]==["$.probable_cause.supporting_finding_ids[0]: unknown reference 'missing'"]
    assert issues[0].code=="unknown_reference"
def test_a_resolvable_supporting_finding_is_accepted():
    d=copy.deepcopy(data()); d["probable_cause"]["supporting_finding_ids"]=[d["findings"][0]["id"]]
    assert validator().validate(d)==[]
def test_a_malformed_probable_cause_is_declared_not_judged():
    # Le validateur ne dit pas quelle forme le noeud devrait avoir — ce sera au
    # contrat. Il déclare seulement qu'il ne peut y appliquer aucune règle.
    d=copy.deepcopy(data()); d["probable_cause"]="cause probable"
    assert [str(x) for x in validator().validate(d)]==["$.probable_cause: malformed: object expected"]
def test_a_malformed_supporting_list_invents_no_reference():
    d=copy.deepcopy(data()); d["probable_cause"]["supporting_finding_ids"]="finding-001"
    assert [str(x) for x in validator().validate(d)]==["$.probable_cause.supporting_finding_ids: malformed: list expected"]

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



# --- Support commun aux deux validations -----------------------------------

def test_business_diagnostics_carry_their_source_and_code():
    d=copy.deepcopy(data()); d["findings"][0]["evidence_ids"]=["missing"]
    unresolved=[x for x in validator().validate(d) if x.code=="unknown_reference"]
    assert len(unresolved)==1
    assert unresolved[0].source=="business"
    # Un écart métier porte sur la source, aucun contrat nommé n'est en cause.
    assert unresolved[0].component is None
    assert str(unresolved[0])=="$.findings[0].evidence_ids[0]: unknown reference 'missing'"

def test_a_business_diagnostic_keeps_its_own_text():
    # Le support est commun, les textes ne le sont pas : un diagnostic métier
    # ne se met pas à ressembler à un diagnostic de schéma.
    d=copy.deepcopy(data()); d["evidence"].append(copy.deepcopy(d["evidence"][0]))
    duplicated=[x for x in validator().validate(d) if x.code=="duplicate_id"]
    assert [str(x) for x in duplicated]==["$.evidence[1].id: duplicate id 'evidence-001'"]

# --- Unicité des identifiants d'occurrence ---------------------------------
#
# Six blocs répétables, une seule règle. L'unicité n'était contrôlée que sur les
# trois blocs que d'autres référencent — elle avait été posée comme prérequis
# des références. Mais la résolution instancie **toute** occurrence par son
# identifiant : deux entrées qui le partagent composent deux fois la première,
# et la seconde disparaît du rapport sans diagnostic.

REPEATABLE=("findings","recommendations","evidence","risks","actions_taken","investigations")

@pytest.mark.parametrize("node",REPEATABLE)
def test_a_duplicate_occurrence_identifier_is_rejected(node):
    d=copy.deepcopy(data())
    entries=d.get(node)
    assert entries, f"la source de référence ne porte aucune occurrence de {node}"
    d[node]=[copy.deepcopy(entries[0]),copy.deepcopy(entries[0])]
    duplicated=[x for x in validator().validate(d) if x.code=="duplicate_id"]
    assert [x.path for x in duplicated]==[f"$.{node}[1].id"]

@pytest.mark.parametrize("node",REPEATABLE)
def test_distinct_identifiers_raise_nothing(node):
    # L'autre moitié de la règle : elle ne se déclenche pas sur des occurrences
    # légitimement répétées.
    d=copy.deepcopy(data())
    second=copy.deepcopy(d[node][0]); second["id"]=f"{second['id']}-bis"
    d[node]=[copy.deepcopy(d[node][0]),second]
    assert [x for x in validator().validate(d) if x.code=="duplicate_id"]==[]

def test_the_command_line_runs_both_validations(tmp_path):
    """La rencontre des deux validations a lieu ici, pas dans `validate`."""
    d=copy.deepcopy(data())
    d["findings"][0]["severity"]="urgent"                            # forme
    d["recommendations"][0]["related_finding_ids"]=["finding-404"]   # métier
    broken=tmp_path/"broken.json"; broken.write_text(json.dumps(d),encoding="utf-8")
    result=subprocess.run([sys.executable,str(VPATH),str(broken)],capture_output=True,text=True)
    assert result.returncode==1
    assert "C-004-finding: $.findings[0].severity:" in result.stderr  # contrat de forme
    assert "unknown reference 'finding-404'" in result.stderr         # règle métier

def test_the_command_line_accepts_the_reference_source():
    result=subprocess.run([sys.executable,str(VPATH),str(DPATH)],capture_output=True,text=True)
    assert result.returncode==0, result.stderr


# Modules que le validateur a le droit de charger. Tous neutres : ils ne
# dépendent ni du moteur de composition, ni d'un format de sortie. La liste est
# explicite plutôt que préfixée, de façon qu'un module nouveau soit un choix et
# non un effet de bord.
NEUTRAL_MODULES={"adc_profile","adc_profile.contract","adc_profile.resolution",
                 "adc_contracts","adc_diagnostics"}

def test_validator_does_not_depend_on_the_engine():
    """Contrôle statique : le source ne mentionne que des modules neutres."""
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
    loaded=set(result.stdout.split())
    assert "adc_profile" in loaded  # le noyau neutre est bien chargé
    assert loaded<=NEUTRAL_MODULES, f"module non neutre chargé : {sorted(loaded-NEUTRAL_MODULES)}"

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
