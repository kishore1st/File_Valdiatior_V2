import { useState } from "react";
import { sha256Hex } from "../utils/sha256";
import { api } from "../api/client";

export default function FileUploader() {
  const [files, setFiles] = useState<File[]>([]);
  const [schema, setSchema] = useState("customer");
  const [region, setRegion] = useState("IN");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<any>(null);

  async function submit() {
    if (!files.length) return;
    setBusy(true);
    try {
      // Client-side hash (advisory) — backend recomputes
      await Promise.all(files.map(sha256Hex));
      const fd = new FormData();
      fd.append("schema_type_key", schema);
      fd.append("region_code", region);
      files.forEach(f => fd.append("files", f));
      const { data } = await api.post("/batches", fd);
      setResult(data);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section>
      <input type="file" multiple accept=".csv,.xlsx"
             onChange={e => setFiles(Array.from(e.target.files || []))} />
      <select value={schema} onChange={e => setSchema(e.target.value)}>
        <option value="customer">Customer</option>
        <option value="transaction">Transaction</option>
      </select>
      <select value={region} onChange={e => setRegion(e.target.value)}>
        {["IN", "US", "EU", "GB", "AE"].map(r => <option key={r}>{r}</option>)}
      </select>
      <button onClick={submit} disabled={!files.length || busy}>
        {busy ? "Uploading…" : `Upload ${files.length} file(s)`}
      </button>
      {result && <pre>{JSON.stringify(result, null, 2)}</pre>}
    </section>
  );
}