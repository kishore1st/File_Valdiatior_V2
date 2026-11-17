import React, { useState, useRef } from "react";

/* ------------------------------------------------------------------ */
/*  Design tokens (match Data Portal smart screens)                    */
/* ------------------------------------------------------------------ */
const T = {
  bg: "#eef1f6", card: "#ffffff", border: "#e2e7f0", text: "#1c2733",
  muted: "#6b7787", accent: "#2f6fed", accentLight: "#e8f0fe",
  green: "#159a5b", greenBg: "#e4f6ec", red: "#d63b3b", redBg: "#fdecec",
  amber: "#b7791f", amberBg: "#fdf3e3", rail: "#16233a", radius: 10,
};
const S = {
  app: { display: "flex", flexDirection: "column", height: "100vh", overflow: "hidden", background: T.bg, fontFamily: '"Segoe UI",Roboto,Arial,sans-serif', fontSize: 13, color: T.text },
  topbar: { height: 50, background: "#fff", borderBottom: `1px solid ${T.border}`, display: "flex", alignItems: "center", gap: 14, padding: "0 18px", flex: "none" },
  logo: { fontWeight: 800, fontSize: 15, color: T.rail },
  gsearch: { flex: 1, maxWidth: 380, display: "flex", alignItems: "center", gap: 8, background: "#f1f4f9", borderRadius: 8, padding: "7px 12px", color: T.muted },
  env: { background: T.amberBg, color: T.amber, fontWeight: 700, fontSize: 11, padding: "3px 10px", borderRadius: 11 },
  body: { display: "flex", flex: 1, minHeight: 0 },
  rail: { width: 54, background: T.rail, display: "flex", flexDirection: "column", padding: "10px 0", flex: "none" },
  railA: (active) => ({ display: "flex", alignItems: "center", gap: 12, color: active ? "#fff" : "#aebbd4", padding: "11px 0 11px 16px", background: active ? T.accent : "transparent", fontWeight: active ? 700 : 400, whiteSpace: "nowrap", overflow: "hidden", textDecoration: "none" }),
  content: { flex: 1, overflow: "auto", padding: "16px 22px" },
  pagehead: { display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 },
  h1: { fontSize: 18, fontWeight: 700, margin: 0 },
  crumb: { fontSize: 11.5, color: T.muted, marginTop: 2 },
  chips: { display: "flex", gap: 8 },
  chip: { background: "#fff", border: `1px solid ${T.border}`, borderRadius: 9, padding: "6px 12px", display: "flex", alignItems: "center", gap: 6 },
  card: { background: T.card, border: `1px solid ${T.border}`, borderRadius: T.radius, padding: "14px 16px" },
  btn: (kind) => ({
    border: kind === "ghost" ? `1px solid ${T.border}` : 0, borderRadius: 7, padding: "7px 14px",
    fontSize: 12.5, cursor: "pointer", fontWeight: 600, whiteSpace: "nowrap",
    background: kind === "primary" ? T.accent : kind === "green" ? T.green : kind === "danger" ? T.red : "#fff",
    color: ["primary", "green", "danger"].includes(kind) ? "#fff" : T.text,
  }),
  badge: (c) => ({ display: "inline-block", padding: "2px 9px", borderRadius: 10, fontSize: 11, fontWeight: 700,
    background: c === "ok" ? T.greenBg : c === "err" ? T.redBg : c === "warn" ? T.amberBg : T.accentLight,
    color: c === "ok" ? T.green : c === "err" ? T.red : c === "warn" ? T.amber : T.accent }),
  mono: { fontFamily: "Consolas,Menlo,monospace" },
  hint: { fontSize: 11.5, color: T.muted, lineHeight: 1.55 },
  input: { padding: "7px 9px", border: `1px solid ${T.border}`, borderRadius: 7, fontSize: 12.5, width: "100%" },
  label: { display: "block", fontSize: 11, color: T.muted, marginBottom: 3, fontWeight: 700 },
  toast: (kind) => ({ borderRadius: 8, padding: "9px 12px", fontSize: 12.5, display: "flex", gap: 8, marginTop: 10,
    background: kind === "ok" ? T.greenBg : kind === "err" ? T.redBg : T.amberBg,
    border: `1px solid ${kind === "ok" ? "#b9e6cd" : kind === "err" ? "#f3c2c2" : "#f0dcb8"}` }),
};

const TEMPLATE = `# Data Contract — define once, enforce at upload
dataset: new_dataset
version: 1.0.0
owner: data-ops@corp.local
description: ""
family: Sales Transactions
region: EMEA

schema:
  - name: txn_id
    type: string
    required: true
    checks: ["not_null", "unique"]
  - name: amount
    type: decimal
    required: true
    checks: ["> 0"]
  - name: region
    type: string
    required: true
    checks: ["in: regions"]

sla:
  freshness: daily
  retention_days: 90
`;

const seed = [
  { id: "c1", name: "sales_transactions", dataset: "sales_transactions", version: "2.1.0", status: "Active", updated: "2026-11-08", yaml: "" },
  { id: "c2", name: "customer_master", dataset: "customer_master", version: "1.4.2", status: "Active", updated: "2026-10-30", yaml: "" },
  { id: "c3", name: "inventory_snapshot", dataset: "inventory_snapshot", version: "0.9.0", status: "Draft", updated: "2026-11-11", yaml: "" },
];

const yamlOf = (c) => c.yaml || `# ${c.dataset} — v${c.version}\ndataset: ${c.dataset}\nversion: ${c.version}\nstatus: ${c.status.toLowerCase()}\n`;

function extractKey(yaml, key) {
  const m = yaml.match(new RegExp(`^\\s*${key}:\\s*(.+)$`, "m"));
  return m ? m[1].replace(/['"]/g, "").trim() : "";
}
function patchKey(yaml, key, value) {
  const re = new RegExp(`^(\\s*${key}:).*$`, "m");
  return re.test(yaml) ? yaml.replace(re, `$1 ${value}`) : `${key}: ${value}\n${yaml}`;
}
function validate(yaml) {
  const errs = [];
  if (!extractKey(yaml, "dataset")) errs.push("Missing required key: dataset");
  const v = extractKey(yaml, "version");
  if (v && !/^\d+\.\d+\.\d+$/.test(v)) errs.push(`version "${v}" must be semver (e.g. 1.0.0)`);
  if (!/schema:\s*\n(\s+-\s+name:)/.test(yaml)) errs.push("schema: must list at least one field (- name: ...)");
  const opens = (yaml.match(/\[/g) || []).length, closes = (yaml.match(/\]/g) || []).length;
  if (opens !== closes) errs.push("Unbalanced square brackets in checks lists");
  const oc = (yaml.match(/\{/g) || []).length, cc = (yaml.match(/\}/g) || []).length;
  if (oc !== cc) errs.push("Unbalanced curly braces");
  return errs;
}

export default function DataContractScreen() {
  const [contracts, setContracts] = useState(seed);
  const [activeId, setActiveId] = useState("c1");
  const active = contracts.find((c) => c.id === activeId) || contracts[0];
  const [yaml, setYaml] = useState(yamlOf(active));
  const [meta, setMeta] = useState({ dataset: active.dataset, version: active.version });
  const [msg, setMsg] = useState(null);
  const fileRef = useRef(null);
  const gutterRef = useRef(null);

  const openContract = (c) => {
    setActiveId(c.id); setYaml(yamlOf(c));
    setMeta({ dataset: c.dataset, version: c.version }); setMsg(null);
  };

  const onUpload = (e) => {
    const f = e.target.files[0];
    if (!f) return;
    const reader = new FileReader();
    reader.onload = () => {
      const text = reader.result;
      const errs = validate(text);
      const dataset = extractKey(text, "dataset") || f.name.replace(/\.ya?ml$/i, "");
      const version = extractKey(text, "version") || "0.1.0";
      const exists = contracts.some((c) => c.dataset === dataset);
      setContracts((cs) => exists
        ? cs.map((c) => c.dataset === dataset ? { ...c, version, yaml: text, updated: "2026-11-12" } : c)
        : [...cs, { id: "c" + Date.now(), name: dataset, dataset, version, status: "Draft", updated: "2026-11-12", yaml: text }]);
      const id = exists ? contracts.find((c) => c.dataset === dataset).id : "c" + Date.now();
      setActiveId(id); setYaml(text); setMeta({ dataset, version });
      setMsg(errs.length
        ? { kind: "err", title: `Uploaded ${f.name} — ${errs.length} validation issue(s)`, items: errs }
        : { kind: "ok", title: `Uploaded & parsed: ${f.name} → dataset "${dataset}" v${version}`, items: [] });
    };
    reader.readAsText(f);
    e.target.value = "";
  };

  const onNew = () => {
    const id = "c" + Date.now();
    const c = { id, name: "new_dataset", dataset: "new_dataset", version: "1.0.0", status: "Draft", updated: "2026-11-12", yaml: TEMPLATE };
    setContracts((cs) => [c, ...cs]); setActiveId(id); setYaml(TEMPLATE);
    setMeta({ dataset: "new_dataset", version: "1.0.0" });
    setMsg({ kind: "ok", title: "New draft created from template — edit dataset & schema, then Save", items: [] });
  };

  const updateMeta = (key, value) => {
    setMeta((m) => ({ ...m, [key]: value }));
    setYaml((y) => patchKey(y, key, value));
  };

  const onSave = () => {
    const errs = validate(yaml);
    if (errs.length) { setMsg({ kind: "err", title: "Cannot save — fix these first:", items: errs }); return; }
    const dataset = extractKey(yaml, "dataset"), version = extractKey(yaml, "version");
    const dup = contracts.find((c) => c.dataset === dataset && c.id !== activeId);
    if (dup) { setMsg({ kind: "err", title: `Dataset "${dataset}" already exists (v${dup.version}). Bump the version or rename.`, items: [] }); return; }
    setContracts((cs) => cs.map((c) => c.id === activeId ? { ...c, name: dataset, dataset, version, yaml, updated: "2026-11-12", status: c.status === "Draft" ? "Draft" : c.status } : c));
    setMsg({ kind: "ok", title: `Saved contract "${dataset}" v${version}`, items: [] });
  };

  const onValidate = () => {
    const errs = validate(yaml);
    setMsg(errs.length
      ? { kind: "err", title: `${errs.length} issue(s) found`, items: errs }
      : { kind: "ok", title: "Contract is valid — ready to save", items: [] });
  };

  const lines = yaml.split("\n").length;

  return (
    <div style={S.app}>
      <div style={S.topbar}>
        <div style={S.logo}>◆ Data<span style={{ color: T.accent }}>Portal</span></div>
        <div style={S.gsearch}>🔍 <input placeholder="Search contracts, datasets, owners…" /></div>
        <span style={{ flex: 1 }}></span>
        <span style={S.env}>UAT</span>
        <span style={{ display: "inline-flex", alignItems: "center", justifyContent: "center", width: 30, height: 30, borderRadius: "50%", background: T.accent, color: "#fff", fontWeight: 700 }}>AK</span>
      </div>
      <div style={S.body}>
        <div style={S.rail}>
          <a href="upload.html" style={S.railA(false)}><span style={{ width: 22, textAlign: "center" }}>⬆️</span></a>
          <a href="lifecycle.html" style={S.railA(false)}><span style={{ width: 22, textAlign: "center" }}>🔄</span></a>
          <a href="admin.html" style={S.railA(false)}><span style={{ width: 22, textAlign: "center" }}>🛡️</span></a>
          <a href="manager.html" style={S.railA(false)}><span style={{ width: 22, textAlign: "center" }}>⚙️</span></a>
          <a href="data-contract-demo.html" style={S.railA(true)}><span style={{ width: 22, textAlign: "center" }}>⎘</span></a>
        </div>

        <div style={S.content}>
          <div style={S.pagehead}>
            <div><h1 style={S.h1}>Data Contracts (YAML)</h1><div style={S.crumb}>Portal / Manager / Contracts</div></div>
            <div style={S.chips}>
              <div style={S.chip}><b>{contracts.length}</b><span style={S.hint}>contracts</span></div>
              <div style={S.chip}><b style={{ color: T.green }}>{contracts.filter((c) => c.status === "Active").length}</b><span style={S.hint}>active</span></div>
              <div style={S.chip}><b style={{ color: T.amber }}>{contracts.filter((c) => c.status === "Draft").length}</b><span style={S.hint}>draft</span></div>
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "250px 1fr 300px", gap: 14, alignItems: "start" }}>
            {/* -------- Left: contract list -------- */}
            <div style={S.card}>
              <div style={{ display: "flex", gap: 8, marginBottom: 10 }}>
                <input ref={fileRef} type="file" accept=".yaml,.yml" style={{ display: "none" }} onChange={onUpload} />
                <button style={{ ...S.btn("ghost"), flex: 1 }} onClick={() => fileRef.current.click()}>⬆ Upload YAML</button>
                <button style={{ ...S.btn("primary"), flex: 1 }} onClick={onNew}>＋ New</button>
              </div>
              <div style={{ ...S.hint, marginBottom: 8, fontWeight: 700 }}>CONTRACTS</div>
              {contracts.map((c) => (
                <div key={c.id} onClick={() => openContract(c)} style={{
                  padding: "9px 10px", borderRadius: 8, cursor: "pointer", marginBottom: 6,
                  border: `1px solid ${c.id === activeId ? T.accent : T.border}`,
                  background: c.id === activeId ? T.accentLight : "#fff",
                }}>
                  <div style={{ fontWeight: 700, fontSize: 12.5 }}>{c.dataset}</div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 4 }}>
                    <span style={S.mono, S.hint}>v{c.version}</span>
                    <span style={S.badge(c.status === "Active" ? "ok" : "warn")}>{c.status}</span>
                  </div>
                </div>
              ))}
            </div>

            {/* -------- Center: YAML editor -------- */}
            <div style={S.card}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
                <div style={{ fontWeight: 700 }}><span style={S.mono}>{active ? active.dataset + ".yaml" : "contract.yaml"}</span></div>
                <div style={{ display: "flex", gap: 8 }}>
                  <button style={S.btn("ghost")} onClick={onValidate}>✓ Validate</button>
                  <button style={S.btn("primary")} onClick={onSave}>💾 Save Contract</button>
                </div>
              </div>
              <div style={{ display: "flex", border: `1px solid ${T.border}`, borderRadius: 8, overflow: "hidden", background: "#fbfcfe" }}>
                <div ref={gutterRef} style={{
                  padding: "10px 8px", textAlign: "right", color: "#9aa7ba", fontSize: 12, lineHeight: "18px",
                  fontFamily: "Consolas,Menlo,monospace", background: "#f4f6fb", borderRight: `1px solid ${T.border}`,
                  userSelect: "none", minWidth: 34,
                }}>
                  {Array.from({ length: lines }, (_, i) => <div key={i}>{i + 1}</div>)}
                </div>
                <textarea
                  value={yaml} spellCheck="false"
                  onChange={(e) => setYaml(e.target.value)}
                  onScroll={(e) => { if (gutterRef.current) gutterRef.current.scrollTop = e.target.scrollTop; }}
                  style={{
                    flex: 1, border: 0, outline: "none", resize: "none", padding: "10px 12px",
                    fontFamily: "Consolas,Menlo,monospace", fontSize: 12.5, lineHeight: "18px",
                    minHeight: 420, background: "transparent", color: T.text, tabSize: 2,
                  }}
                />
              </div>
              <div style={S.hint}>Upload an existing <b>.yaml / .yml</b> contract, edit it for a new dataset (change <span style={S.mono}>dataset:</span>, bump <span style={S.mono}>version:</span>, adjust <span style={S.mono}>schema:</span>), then Save. Uploading a file whose <span style={S.mono}>dataset:</span> already exists updates that contract.</div>
            </div>

            {/* -------- Right: properties + messages -------- */}
            <div>
              <div style={S.card}>
                <div style={{ fontWeight: 700, marginBottom: 10 }}>Properties</div>
                <div style={{ marginBottom: 10 }}>
                  <label style={S.label}>DATASET</label>
                  <input style={S.input} value={meta.dataset} onChange={(e) => updateMeta("dataset", e.target.value)} />
                </div>
                <div style={{ marginBottom: 10 }}>
                  <label style={S.label}>VERSION</label>
                  <input style={S.input} value={meta.version} onChange={(e) => updateMeta("version", e.target.value)} />
                </div>
                <div style={{ marginBottom: 10 }}>
                  <label style={S.label}>OWNER</label>
                  <input style={S.input} defaultValue={extractKey(yaml, "owner")} onChange={(e) => setYaml((y) => patchKey(y, "owner", e.target.value))} />
                </div>
                <div style={{ display: "flex", gap: 8 }}>
                  <div style={{ flex: 1 }}>
                    <label style={S.label}>FAMILY</label>
                    <select style={S.input} value={extractKey(yaml, "family")} onChange={(e) => setYaml((y) => patchKey(y, "family", e.target.value))}>
                      {["Sales Transactions", "Customer Master", "Inventory Snapshot", "Financial GL"].map((f) => <option key={f}>{f}</option>)}
                    </select>
                  </div>
                  <div style={{ flex: 1 }}>
                    <label style={S.label}>REGION</label>
                    <select style={S.input} value={extractKey(yaml, "region")} onChange={(e) => setYaml((y) => patchKey(y, "region", e.target.value))}>
                      {["EMEA", "North America", "APAC", "LatAm"].map((r) => <option key={r}>{r}</option>)}
                    </select>
                  </div>
                </div>
              </div>

              <div style={S.card}>
                <div style={{ fontWeight: 700, marginBottom: 8 }}>Validation</div>
                {!msg && <div style={S.hint}>Run Validate, or Save — the contract is checked automatically.</div>}
                {msg && (
                  <div style={S.toast(msg.kind)}>
                    <div>
                      <div>{msg.kind === "ok" ? "✅" : "⛔"} <b>{msg.title}</b></div>
                      {msg.items.length > 0 && (
                        <ul style={{ margin: "6px 0 0 16px" }}>{msg.items.map((i, k) => <li key={k} style={{ margin: "2px 0" }}>{i}</li>)}</ul>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}