import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { GradeMark, Notice, Skeleton, StatusMark, SeverityTag } from "../components/primitives";

export default function ScanDetail() {
  const { scanId } = useParams();
  const [exportError, setExportError] = useState("");
  const scan = useQuery({
    queryKey: ["scan", scanId], queryFn: () => api.getScan(scanId),
    refetchInterval: q => ["queued", "running"].includes(q.state.data?.status) ? 2000 : false,
  });
  if (scan.isPending) return <Skeleton lines={6} />;
  if (scan.isError) return <Notice tone="error" title="Could not load scan">{scan.error.message}</Notice>;
  const data = scan.data;
  const raw = data.raw_results ?? {};
  const running = ["queued", "running"].includes(data.status);
  const results = [
    ...Object.entries(raw.evasion ?? {}), ...Object.entries(raw.black_box ?? {}),
    ...Object.entries(raw.poisoning ?? {}).map(([key, value]) => [`poisoning ${key}`, value]),
  ];
  async function download(format) {
    setExportError("");
    try { await api.downloadReport(scanId, format); }
    catch (err) { setExportError(err.message); }
  }
  return <div className="mx-auto max-w-6xl">
    <p className="t-label">Scan {scanId.slice(0, 8)}</p>
    <h1 className="t-display mt-3">{running ? "Running" : data.status === "failed" ? "Scan failed" : "Scan results"}</h1>
    <div className="mt-6 flex flex-wrap gap-6 text-sm"><StatusMark status={data.status} />
      <span>{data.threat_model.replaceAll("_", " ")}</span>
      <Link className="link-underline" to={`/models/${data.model_id}`}>Model history</Link>
    </div>
    {running && <p className="mt-16 text-muted">The evaluator is running your selected attacks. This page refreshes automatically.</p>}
    {data.status === "failed" && <section className="mt-16"><Notice tone="error" title="Evaluation failed">{data.error}</Notice>
      <Link className="btn btn-ghost mt-5" to={`/scans/new?model=${data.model_id}`}>Configure another scan</Link></section>}
    {data.status === "done" && data.score && <>
      <section className="mt-16 rule pt-8 grid gap-8 md:grid-cols-2">
        <div><h2 className="t-head">Robustness</h2><div className="mt-8"><GradeMark grade={data.score.grade} score={data.score.final_score_0_100} /></div></div>
        <div>{Object.entries(data.score.component_scores).map(([name, value]) => <div key={name} className="rule py-4 flex justify-between gap-5">
          <span>{name.replaceAll("_", " ")}</span><span className="t-data">{value.toFixed(3)} · weight {data.score.weights[name].toFixed(2)}</span>
        </div>)}<p className="mt-5 text-sm text-muted">Score = 100 × (1 − weighted attack impact). Weights cover tested categories only. A high score is not a security certification.</p></div>
      </section>
      <section className="mt-16 rule pt-8"><h2 className="t-head">Evaluation evidence</h2>
        <p className="mt-4 text-muted">{raw.dataset_description ?? "Legacy result: evaluation provenance unavailable"}</p>
        <p className="mt-3 text-sm">Clean accuracy: {((raw.clean_accuracy ?? 0) * 100).toFixed(1)}% · {raw.sample_count ?? "?"} samples · {raw.eligible_count ?? "?"} initially correct · Seed {raw.seed ?? "?"}</p>
        <p className="mt-3 text-sm text-muted max-w-measure">{raw.limitations}</p>
        <p className="mt-3 text-xs break-all font-mono">Model SHA-256: {raw.model_sha256 ?? "unavailable"}</p>
        <p className="mt-2 text-xs break-all font-mono">Dataset SHA-256: {raw.dataset_sha256 ?? "unavailable"}</p>
      </section>
      <section className="mt-16 rule pt-8"><h2 className="t-head">Attack outcomes</h2>
        <p className="mt-4 text-sm text-muted">ASR is the share of initially correct samples misclassified after attack. Poisoning measures accuracy lost against a clean retraining control.</p>
        <div className="mt-8 overflow-x-auto"><table className="w-full text-left text-sm"><thead><tr className="border-b border-rule">
          {["Attack", "ASR / accuracy drop", "Accuracy after attack", "Evidence"].map(x => <th className="py-3 pr-5" key={x}>{x}</th>)}</tr></thead>
          <tbody>{results.map(([name, block]) => <tr className="border-b border-rule" key={name}>
            <td className="py-4 pr-5 uppercase">{name}</td><td className="py-4 pr-5">{((block.asr ?? block.accuracy_drop) * 100).toFixed(1)}%</td>
            <td className="py-4 pr-5">{((block.adversarial_accuracy ?? block.poisoned_accuracy ?? 0) * 100).toFixed(1)}%</td>
            <td className="py-4">{block.eligible_count != null ? `${block.success_count} / ${block.eligible_count} successful` : `${block.poisoned_count} labels flipped`}</td>
          </tr>)}</tbody></table></div>
        <details className="mt-6"><summary className="cursor-pointer text-sm">Inspect parameters and adversarial samples</summary>
          <pre className="mt-3 max-h-96 overflow-auto bg-panel p-4 text-xs">{JSON.stringify(raw, null, 2)}</pre></details>
      </section>
      <section className="mt-16 rule pt-8"><h2 className="t-head">Findings and mitigations</h2>
        {!data.findings.length && <p className="mt-5 text-muted">No successful attack was observed under these test conditions.</p>}
        {data.findings.map((f, i) => <article key={`${f.attack}-${i}`} className="rule py-6 mt-6">
          <div className="flex gap-4 items-center"><h3 className="t-sub uppercase">{f.attack}</h3><SeverityTag severity={f.severity} /></div>
          <p className="mt-3 text-sm"><a className="link-underline" target="_blank" rel="noreferrer" href={`https://atlas.mitre.org/techniques/${f.atlas_technique}`}>{f.atlas_technique}</a> · {f.atlas_tactic}</p>
          <p className="mt-4 max-w-measure">{f.mitigation}</p><p className="mt-3 text-sm text-muted">{f.owasp_ml_top10} · {f.nist_ai_rmf} (informational mapping)</p>
        </article>)}
      </section>
      <section className="mt-16 rule pt-8"><h2 className="t-head">Export assessment</h2>
        <div className="mt-6 flex gap-4"><button className="btn btn-solid" onClick={() => download("pdf")}>Download PDF</button>
          <button className="btn btn-ghost" onClick={() => download("html")}>Download HTML</button>
          <button className="btn btn-ghost" onClick={() => {
            const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], {type: "application/json"}));
            const a = document.createElement("a"); a.href = url; a.download = `scan-${scanId}.json`; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
          }}>Export JSON</button></div>
        {exportError && <p role="alert" className="mt-4 text-signal">{exportError}</p>}
      </section>
    </>}
  </div>;
}
