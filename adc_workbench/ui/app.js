"use strict";

/* Workbench — rendu d'un instantané.
 *
 * Cette page affiche, sélectionne et filtre. Elle ne valide rien, ne résout
 * rien, ne traduit rien et ne déduit rien (ADR-0014). Tout ce qu'elle montre
 * vient d'un champ de l'instantané ; ce que l'instantané ne porte pas n'est pas
 * affichable ici.
 *
 * Le DOM est construit par `createElement` et `textContent` exclusivement :
 * aucun contenu observé n'est jamais interprété comme du balisage. C'est une
 * propriété de construction, pas une précaution ponctuelle — une mission dont un
 * champ contient du HTML s'affiche comme du texte.
 */

const $ = (id) => document.getElementById(id);

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined && text !== null) node.textContent = String(text);
  return node;
}

/** Rend une ligne sélectionnable au sein de son panneau. */
function selectable(node, panel) {
  node.addEventListener("click", () => {
    panel.querySelectorAll(".selected").forEach((n) => n.classList.remove("selected"));
    node.classList.add("selected");
  });
  return node;
}

function empty(message) {
  return el("p", "empty", message);
}

function group(title, count, kind) {
  const head = el("div", kind ? `group-title ${kind}` : "group-title");
  head.appendChild(el("span", null, title));
  if (count !== undefined) {
    head.appendChild(document.createTextNode(" "));
    head.appendChild(el("span", "count", `(${count})`));
  }
  return head;
}

/* --- Bandeau ------------------------------------------------------------ */

function fact(term, value, className) {
  const wrap = el("div", "fact");
  wrap.appendChild(el("dt", null, term));
  wrap.appendChild(el("dd", className, value));
  return wrap;
}

function renderBanner(snapshot) {
  const facts = $("banner-facts");
  facts.textContent = "";
  facts.appendChild(fact("mission", snapshot.mission ? snapshot.mission.path : "—"));
  facts.appendChild(fact("profil", snapshot.profile_id));
  facts.appendChild(fact("composants résolus", snapshot.resolution.length));

  // Deux faits de l'instantané, jamais un statut global inventé.
  const refused = snapshot.contract_diagnostics.length > 0;
  facts.appendChild(
    refused
      ? fact("contrat", `refusé — ${snapshot.contract_diagnostics.length} écart(s)`, "flag-refused")
      : fact("contrat", "aucun écart")
  );
  facts.appendChild(
    fact(
      "document",
      snapshot.document ? "composé" : "non composé",
      snapshot.document ? "flag-composed" : "flag-refused"
    )
  );
  if (snapshot.observation_notes.length) {
    facts.appendChild(fact("notes d'observation", snapshot.observation_notes.length));
  }
}

/* --- Mission ------------------------------------------------------------ */

function renderMission(snapshot) {
  const body = $("body-mission");
  body.textContent = "";
  if (!snapshot.mission) {
    body.appendChild(empty("Aucune mission observée — instantané construit depuis une source."));
    return;
  }
  body.appendChild(group("artefacts", snapshot.mission.artefacts.length));

  for (const artefact of snapshot.mission.artefacts) {
    const row = el("div", "row");
    row.dataset.filter = artefact.path;
    row.appendChild(el("div", "mono", artefact.path));

    const meta = el("div", "meta");
    meta.appendChild(el("span", null, artefact.kind));
    meta.appendChild(el("span", null, artefact.size === null ? "—" : `${artefact.size} o`));
    // Absence de rôle rendue comme telle : aucune propagation n'est ajoutée.
    meta.appendChild(
      artefact.role === null ? el("span", "none", "sans rôle déclaré") : el("span", null, artefact.role)
    );
    meta.appendChild(el("span", "tag" + (artefact.content !== null ? " on" : ""),
      artefact.content !== null ? "contenu chargé" : "contenu non chargé"));
    if (artefact.consumed) meta.appendChild(el("span", "tag on", "lu par l'observation"));
    row.appendChild(meta);

    if (artefact.content !== null) {
      const content = el("pre", null, artefact.content);
      content.hidden = true;
      row.appendChild(content);
      row.addEventListener("click", () => { content.hidden = !content.hidden; });
    }
    body.appendChild(selectable(row, body));
  }
}

/* --- Source canonique --------------------------------------------------- */

function jsonNode(key, value) {
  const wrap = el("div", "node");
  const isObject = value !== null && typeof value === "object";

  if (!isObject) {
    const entry = el("div", "entry");
    if (key !== null) {
      entry.appendChild(el("span", "key", `${key}: `));
    }
    const type = value === null ? "null" : typeof value;
    entry.appendChild(el("span", `value ${type}`, value === null ? "null" : String(value)));
    entry.dataset.filter = `${key} ${value}`;
    wrap.appendChild(entry);
    return wrap;
  }

  const entries = Array.isArray(value)
    ? value.map((item, index) => [index, item])
    : Object.entries(value);
  const details = el("details");
  details.open = true;
  const label = Array.isArray(value) ? `[${entries.length}]` : `{${entries.length}}`;
  details.appendChild(el("summary", null, key === null ? label : `${key} ${label}`));
  for (const [childKey, childValue] of entries) {
    details.appendChild(jsonNode(childKey, childValue));
  }
  wrap.appendChild(details);
  return wrap;
}

function renderSource(snapshot) {
  const body = $("body-source");
  body.textContent = "";
  body.appendChild(group("source observée"));
  body.appendChild(jsonNode(null, snapshot.source));
}

/* --- Diagnostics -------------------------------------------------------- */

function structuredDiagnostic(diagnostic) {
  const row = el("div", "row");
  row.appendChild(el("div", "mono", diagnostic.path));
  row.appendChild(el("div", null, diagnostic.message));
  const meta = el("div", "meta");
  meta.appendChild(el("span", null, `source ${diagnostic.source}`));
  meta.appendChild(el("span", null, `code ${diagnostic.code}`));
  meta.appendChild(
    diagnostic.component === null
      ? el("span", "none", "aucun contrat nommé")
      : el("span", null, diagnostic.component)
  );
  row.appendChild(meta);
  row.dataset.filter = `${diagnostic.path} ${diagnostic.message} ${diagnostic.code} ${diagnostic.component}`;
  return row;
}

function renderDiagnostics(snapshot) {
  const body = $("body-diagnostics");
  body.textContent = "";

  const families = [
    ["contrat", "contract", snapshot.contract_diagnostics, true],
    ["source / métier", "business", snapshot.source_diagnostics, true],
    ["composition", "composition", snapshot.composition_diagnostics, false],
  ];

  for (const [title, kind, items, structured] of families) {
    body.appendChild(group(title, items.length, kind));
    if (!items.length) {
      body.appendChild(empty("aucun diagnostic dans cette famille"));
      continue;
    }
    for (const item of items) {
      // Les diagnostics de composition sont des chaînes libres : ils sont
      // affichés tels quels, jamais découpés pour en tirer une structure.
      const row = structured ? structuredDiagnostic(item) : el("div", "row mono", item);
      if (!structured) row.dataset.filter = item;
      body.appendChild(selectable(row, body));
    }
  }

  if (snapshot.observation_notes.length) {
    body.appendChild(group("notes d'observation", snapshot.observation_notes.length));
    for (const note of snapshot.observation_notes) {
      const row = el("div", "row", note);
      row.dataset.filter = note;
      body.appendChild(selectable(row, body));
    }
  }
}

/* --- Composants --------------------------------------------------------- */

function renderComponents(snapshot) {
  const body = $("body-components");
  body.textContent = "";

  // Les instances de l'IR, indexées par leur identité, pour montrer le payload
  // en regard de l'occurrence résolue. Aucune résolution n'est refaite ici :
  // l'ordre et le contenu de `resolution` sont repris tels quels.
  const payloads = new Map();
  for (const component of snapshot.components) {
    payloads.set(`${component.component_id} ${component.instance_id}`, component.payload);
  }
  const contracts = new Map();
  for (const contract of snapshot.contracts) {
    contracts.set(contract.key, contract);
  }

  body.appendChild(group("occurrences résolues", snapshot.resolution.length));
  if (!snapshot.resolution.length) {
    body.appendChild(empty("aucune occurrence résolue"));
    return;
  }

  for (const block of snapshot.resolution) {
    const row = el("div", "row");
    row.appendChild(el("div", "mono", block.component_id));

    const meta = el("div", "meta");
    meta.appendChild(el("span", null, block.instance_id));
    meta.appendChild(el("span", "tag" + (block.composed ? " on" : ""),
      block.composed ? "composé" : "non composé"));

    // Cardinalité affichée seulement si l'instantané la porte pour cette clé.
    const contract = contracts.get(block.component_id);
    if (contract && contract.minimum !== null && contract.maximum !== null) {
      meta.appendChild(el("span", null, `cardinalité ${contract.minimum}..${contract.maximum}`));
    } else if (contract && contract.minimum !== null) {
      meta.appendChild(el("span", null, `cardinalité ${contract.minimum}..∞`));
    } else {
      meta.appendChild(el("span", "none", "cardinalité inconnue"));
    }
    row.appendChild(meta);

    const payload = payloads.get(`${block.component_id} ${block.instance_id}`);
    if (payload !== undefined) {
      const pre = el("pre", null, JSON.stringify(payload, null, 2));
      pre.hidden = true;
      row.appendChild(pre);
      row.addEventListener("click", () => { pre.hidden = !pre.hidden; });
    } else {
      const absent = el("div", "meta");
      absent.appendChild(el("span", "none", "aucun payload"));
      row.appendChild(absent);
    }

    row.dataset.filter = `${block.component_id} ${block.instance_id}`;
    body.appendChild(selectable(row, body));
  }
}

/* --- Filtres (présentation pure) ---------------------------------------- */

function wireFilter(inputId, bodyId) {
  const input = $(inputId);
  const body = $(bodyId);
  input.addEventListener("input", () => {
    const needle = input.value.toLowerCase();
    for (const row of body.querySelectorAll("[data-filter]")) {
      row.hidden = needle !== "" && !row.dataset.filter.toLowerCase().includes(needle);
    }
  });
}

/* --- Démarrage ---------------------------------------------------------- */

async function main() {
  const response = await fetch("/snapshot.json");
  const snapshot = await response.json();

  renderBanner(snapshot);
  renderMission(snapshot);
  renderSource(snapshot);
  renderDiagnostics(snapshot);
  renderComponents(snapshot);

  wireFilter("filter-mission", "body-mission");
  wireFilter("filter-source", "body-source");
  wireFilter("filter-diagnostics", "body-diagnostics");
  wireFilter("filter-components", "body-components");
}

main();
