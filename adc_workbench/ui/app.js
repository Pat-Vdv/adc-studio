"use strict";

/* Workbench — rendu et navigation par relations.
 *
 * Cette page affiche, sélectionne, met en évidence et filtre. Elle ne valide
 * rien, ne résout rien, ne traduit rien et ne déduit rien (ADR-0014). Tout ce
 * qu'elle montre vient d'un champ de l'instantané.
 *
 * Le DOM est construit par `createElement` et `textContent` exclusivement :
 * aucun contenu observé n'est interprété comme du balisage.
 *
 * Deux règles gouvernent la navigation croisée :
 *
 * - une relation n'existe que si l'instantané fournit **les deux extrémités**
 *   d'une comparaison déterministe. Sans cela, cliquer ne produit rien
 *   ailleurs — l'absence de relation n'est pas comblée par une ressemblance ;
 * - un chemin canonique se **construit** en descendant l'arbre de la source,
 *   jamais ne se **décompose**. Descendre en concaténant est de la
 *   présentation ; découper un chemin reçu serait reconstruire l'arbre qu'une
 *   autre couche connaît.
 */

const $ = (id) => document.getElementById(id);

const PRIMARY = "selected";
const LINKED = "linked";

/* Index de relations, reconstruits à chaque rendu. Ils ne contiennent que des
 * clés venues de l'instantané : aucune table de correspondance n'est écrite
 * ici. */
const sourceNodes = new Map();      // chemin canonique -> élément de l'arbre
const componentRows = new Map();    // identifiant de composant -> éléments
const componentPaths = new Map();   // identifiant de composant -> chemin source

const ROOT_PATH = "$";

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined && text !== null) node.textContent = String(text);
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

/* --- Sélection : un état d'interface, et rien d'autre --------------------
 *
 * Elle ne quitte jamais le DOM : ni instantané, ni serveur, ni stockage. Un
 * rechargement la perd, et c'est la définition même d'un état d'affichage.
 */

function clearSelection() {
  for (const node of document.querySelectorAll(`.${PRIMARY}, .${LINKED}`)) {
    node.classList.remove(PRIMARY, LINKED);
  }
  for (const preview of document.querySelectorAll("[data-preview]")) {
    preview.hidden = true;
  }
}

/**
 * Rend un élément visible dans son panneau, sans jamais bouger la page.
 *
 * Une cible atteinte par relation est **centrée** : elle arrive dans un panneau
 * que l'utilisateur ne regardait pas, et la poser au ras du bord la rendrait
 * lisible sans être trouvable. L'élément cliqué, lui, bouge le moins possible —
 * le déplacer sous le curseur serait désorientant.
 */
function reveal(node, centered) {
  node.scrollIntoView({ block: centered ? "center" : "nearest", inline: "nearest" });
}

/**
 * Applique une sélection primaire et ses mises en évidence liées.
 * Toute sélection antérieure disparaît : aucune trace ne subsiste.
 */
function select(primary, linked) {
  clearSelection();
  primary.classList.add(PRIMARY);
  for (const preview of primary.querySelectorAll("[data-preview]")) {
    preview.hidden = false;
  }
  for (const node of linked || []) {
    if (!node || node === primary) continue;
    node.classList.add(LINKED);
    reveal(node, true);
  }
  reveal(primary, false);
}

function onSelect(node, links) {
  node.addEventListener("click", (event) => {
    event.stopPropagation();
    select(node, typeof links === "function" ? links() : links);
  });
  return node;
}

/* --- Bandeau ------------------------------------------------------------ */

function fact(term, value, className) {
  const wrap = el("div", "fact");
  wrap.appendChild(el("dt", null, term));
  const definition = el("dd", className, value);
  definition.title = String(value);
  wrap.appendChild(definition);
  return wrap;
}

function renderBanner(snapshot) {
  const facts = $("banner-facts");
  facts.textContent = "";
  facts.appendChild(fact("mission", snapshot.mission ? snapshot.mission.path : "—"));
  facts.appendChild(fact("profil", snapshot.profile_id));
  facts.appendChild(fact("composants résolus", snapshot.resolution.length));

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

  const path = $("selected-path");
  path.textContent = "aucune sélection";
  path.classList.add("none");
}

/** Affiche le chemin canonique du nœud sélectionné, ou l'absence de sélection. */
function showPath(path) {
  const target = $("selected-path");
  target.textContent = path === null ? "aucune sélection" : path;
  target.classList.toggle("none", path === null);
  target.title = path === null ? "" : path;
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
    row.dataset.artefact = artefact.path;
    row.appendChild(el("div", "mono", artefact.path));

    const meta = el("div", "meta");
    meta.appendChild(el("span", null, artefact.kind));
    if (artefact.size !== null) meta.appendChild(el("span", null, `${artefact.size} o`));
    meta.appendChild(
      artefact.role === null ? el("span", "none", "sans rôle déclaré") : el("span", null, artefact.role)
    );
    meta.appendChild(el("span", "tag" + (artefact.content !== null ? " on" : ""),
      artefact.content !== null ? "chargé" : "non chargé"));
    if (artefact.consumed) meta.appendChild(el("span", "tag on", "lu par l'observation"));
    row.appendChild(meta);

    if (artefact.content !== null) {
      const content = el("pre", null, artefact.content);
      content.dataset.preview = "";
      content.hidden = true;
      row.appendChild(content);
    }
    // Aucune navigation Mission -> Source : l'instantané ne porte pas cette
    // relation, et la deviner reviendrait à lire le vocabulaire d'atelier.
    body.appendChild(onSelect(row, []));
  }
}

/* --- Source canonique --------------------------------------------------- */

/**
 * Un nœud de l'arbre, et son chemin canonique construit en descendant.
 *
 * `$`, puis `$.bloc`, puis `$.bloc[0].champ` : la même syntaxe que celle des
 * diagnostics, ce qui rend la navigation croisée possible par simple égalité —
 * sans jamais découper un chemin reçu. Aucun nom de nœud réel n'apparaît ici :
 * les chemins sont construits depuis la source observée, pas depuis une liste.
 */
function jsonNode(key, value, path) {
  const wrap = el("div", "node");
  const isObject = value !== null && typeof value === "object";

  if (!isObject) {
    const entry = el("div", "entry");
    if (key !== null) entry.appendChild(el("span", "key", `${key}: `));
    const type = value === null ? "null" : typeof value;
    entry.appendChild(el("span", `value ${type}`, value === null ? "null" : String(value)));
    entry.dataset.filter = `${key} ${value}`;
    registerNode(entry, path);
    wrap.appendChild(entry);
    return wrap;
  }

  const entries = Array.isArray(value)
    ? value.map((item, index) => [index, item])
    : Object.entries(value);
  const details = el("details");
  details.open = true;
  const label = Array.isArray(value) ? `[${entries.length}]` : `{${entries.length}}`;
  const summary = el("summary", null, key === null ? label : `${key} ${label}`);
  summary.dataset.filter = String(key);
  registerNode(summary, path);
  details.appendChild(summary);
  for (const [childKey, childValue] of entries) {
    const childPath = Array.isArray(value) ? `${path}[${childKey}]` : `${path}.${childKey}`;
    details.appendChild(jsonNode(childKey, childValue, childPath));
  }
  wrap.appendChild(details);
  return wrap;
}

function registerNode(node, path) {
  node.dataset.path = path;
  sourceNodes.set(path, node);
  onSelect(node, () => {
    showPath(path);
    // Relation inverse, seulement lorsqu'un contrat désigne exactement ce nœud.
    // Aucun nom de champ n'est reconnu : la comparaison porte sur des chemins.
    const linked = [];
    for (const [componentId, componentPath] of componentPaths) {
      if (componentPath === path) linked.push(...(componentRows.get(componentId) || []));
    }
    return linked;
  });
}

function renderSource(snapshot) {
  const body = $("body-source");
  body.textContent = "";
  sourceNodes.clear();
  body.appendChild(group("source observée"));
  body.appendChild(jsonNode(null, snapshot.source, ROOT_PATH));
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
  row.dataset.diagnostic = diagnostic.code;
  if (diagnostic.component !== null) row.dataset.component = diagnostic.component;
  row.dataset.path = diagnostic.path;
  return row;
}

/** Extrémités que ce diagnostic permet de rejoindre — et elles seules. */
function diagnosticLinks(diagnostic) {
  const linked = [];
  // Un écart métier porte sur la source, pas sur un composant : `component` y
  // est nul, et rien ne doit lui en attribuer un.
  if (diagnostic.component !== null) {
    linked.push(...(componentRows.get(diagnostic.component) || []));
  }
  const node = sourceNodes.get(diagnostic.path);
  if (node) linked.push(node);
  return linked;
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
      if (structured) {
        const row = structuredDiagnostic(item);
        body.appendChild(onSelect(row, () => {
          showPath(item.path);
          return diagnosticLinks(item);
        }));
      } else {
        // Chaîne libre : aucune extrémité n'est disponible, donc aucune
        // navigation. La découper pour en tirer une identité serait
        // reconstruire une structure que le moteur ne produit pas.
        const row = el("div", "row mono", item);
        row.dataset.filter = item;
        row.dataset.unstructured = "";
        body.appendChild(onSelect(row, []));
      }
    }
  }

  if (snapshot.observation_notes.length) {
    body.appendChild(group("notes d'observation", snapshot.observation_notes.length));
    for (const note of snapshot.observation_notes) {
      const row = el("div", "row", note);
      row.dataset.filter = note;
      body.appendChild(onSelect(row, []));
    }
  }
}

/* --- Composants --------------------------------------------------------- */

/**
 * Chemin canonique du nœud qu'un contrat désigne.
 *
 * La table des fragments donne le nom d'un nœud ; l'arbre de la source nomme le
 * même nœud avec le préfixe racine. Préfixer est une mise en forme
 * déterministe — le fait, lui, reste celui que la table déclare.
 */
function canonicalPath(contract) {
  return contract.path === ROOT_PATH ? ROOT_PATH : `${ROOT_PATH}.${contract.path}`;
}

function renderComponents(snapshot) {
  const body = $("body-components");
  body.textContent = "";
  componentRows.clear();
  componentPaths.clear();

  const payloads = new Map();
  for (const component of snapshot.components) {
    payloads.set(`${component.component_id} ${component.instance_id}`, component.payload);
  }
  const contracts = new Map();
  for (const contract of snapshot.contracts) {
    contracts.set(contract.key, contract);
    componentPaths.set(contract.key, canonicalPath(contract));
  }

  body.appendChild(group("occurrences résolues", snapshot.resolution.length));
  if (!snapshot.resolution.length) {
    body.appendChild(empty("aucune occurrence résolue"));
    return;
  }

  for (const block of snapshot.resolution) {
    const row = el("div", "row");
    row.dataset.component = block.component_id;
    row.appendChild(el("div", "mono", block.component_id));

    const meta = el("div", "meta");
    meta.appendChild(el("span", null, block.instance_id));
    meta.appendChild(el("span", "tag" + (block.composed ? " on" : ""),
      block.composed ? "composé" : "non composé"));

    const contract = contracts.get(block.component_id);
    if (contract && contract.minimum !== null && contract.maximum !== null) {
      meta.appendChild(el("span", null, `cardinalité ${contract.minimum}..${contract.maximum}`));
    } else if (contract && contract.minimum !== null) {
      meta.appendChild(el("span", null, `cardinalité ${contract.minimum}..∞`));
    } else {
      meta.appendChild(el("span", "none", "cardinalité inconnue"));
    }
    row.appendChild(meta);

    const payload = payloads.get(`${block.component_id} ${block.instance_id}`);
    if (payload !== undefined) {
      const pre = el("pre", null, JSON.stringify(payload, null, 2));
      pre.dataset.preview = "";
      pre.hidden = true;
      row.appendChild(pre);
    } else {
      const absent = el("div", "meta");
      absent.appendChild(el("span", "none", "aucun payload"));
      row.appendChild(absent);
    }

    row.dataset.filter = `${block.component_id} ${block.instance_id}`;
    if (!componentRows.has(block.component_id)) componentRows.set(block.component_id, []);
    componentRows.get(block.component_id).push(row);

    body.appendChild(onSelect(row, () => {
      const path = componentPaths.get(block.component_id);
      showPath(path === undefined ? null : path);
      const node = path === undefined ? undefined : sourceNodes.get(path);
      return node ? [node] : [];
    }));
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
  // Les composants sont rendus avant la source : ils publient les chemins que
  // les nœuds consulteront pour leur relation inverse.
  renderComponents(snapshot);
  renderSource(snapshot);
  renderDiagnostics(snapshot);

  wireFilter("filter-mission", "body-mission");
  wireFilter("filter-source", "body-source");
  wireFilter("filter-diagnostics", "body-diagnostics");
  wireFilter("filter-components", "body-components");

  document.body.dataset.ready = "";
}

main();
