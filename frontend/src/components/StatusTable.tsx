import { useEffect, useState } from "react";
import { api } from "../api/client";

export default function StatusTable() {
  const [rows, setRows] = useState<any[]>([]);
  const [err, setErr] = useState<string | null>(null);

  async function load() {
    try {
      const { data } = await api.get("/files");
      setRows(data);
      setErr(null);
    } catch (e: any) {
      setErr(e?.response?.data?.detail || e.message);
    }
  }
  useEffect(() => { load(); }, []);

  return (
    <section>
      <h3>Recent files</h3>
      <button onClick={load}>Refresh</button>
      {err && <div style={{ color: "crimson" }}>{err}</div>}
      <table>
        <thead>
          <tr><th>Name</th><th>Region</th><th>Status</th><th>Hash</th></tr>
        </thead>
        <tbody>
          {rows.map(r => (
            <tr key={r.file_id}>
              <td>{r.file_name}</td>
              <td>{r.region_code}</td>
              <td>{r.status}</td>
              <td style={{ fontFamily: "monospace", fontSize: 11 }}>{r.sha256_hash?.slice(0, 12)}…</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}