import { useState, useRef, useCallback } from "react";
import {
  Upload, ArrowRightLeft, Play, CheckCircle2, XCircle, AlertTriangle,
  ChevronDown, ChevronUp, Copy, Download, FileCode2, Loader2, Info,
  Shield, Bug, Wrench, ClipboardCheck, BarChart3, RefreshCw
} from "lucide-react";
import { uploadMigrationFile, runCompleteMigration } from "../services/api";

// ============================================================
// PIPELINE STEPS
// ============================================================

const PIPELINE_STEPS = [
  { key: "analysis",         label: "Migration Analysis",       icon: BarChart3 },
  { key: "conversion",       label: "Java → Julia Conversion",  icon: ArrowRightLeft },
  { key: "risk_analysis",    label: "Migration Risk Analysis",   icon: Shield },
  { key: "error_detection",  label: "Error Detection",           icon: Bug },
  { key: "error_correction", label: "Error Correction",          icon: Wrench },
  { key: "validation",       label: "Functional Validation",     icon: ClipboardCheck },
];

// ============================================================
// SEVERITY BADGE
// ============================================================

function SeverityBadge({ severity }) {
  const colors = {
    HIGH:   "bg-rose-500/15 text-rose-300 border-rose-500/25",
    MEDIUM: "bg-amber-500/15 text-amber-300 border-amber-500/25",
    LOW:    "bg-emerald-500/15 text-emerald-300 border-emerald-500/25",
  };
  return (
    <span className={`inline-flex items-center gap-1 rounded-lg border px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${colors[severity] || colors.MEDIUM}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${severity === "HIGH" ? "bg-rose-400 animate-pulse" : severity === "MEDIUM" ? "bg-amber-400" : "bg-emerald-400"}`} />
      {severity}
    </span>
  );
}

// ============================================================
// COLLAPSIBLE SECTION
// ============================================================

function CollapsibleSection({ title, icon: Icon, children, defaultOpen = false, badge }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="rounded-2xl border border-slate-800/80 bg-slate-950/40 overflow-hidden transition-all">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex w-full items-center gap-3 px-5 py-4 text-left transition hover:bg-slate-800/30"
      >
        {Icon && <Icon size={16} className="text-cyan-300 shrink-0" />}
        <span className="text-sm font-bold text-white flex-1">{title}</span>
        {badge && <span className="text-[10px] font-bold text-cyan-300 bg-cyan-400/10 px-2 py-0.5 rounded-full">{badge}</span>}
        {open ? <ChevronUp size={16} className="text-slate-400" /> : <ChevronDown size={16} className="text-slate-400" />}
      </button>
      {open && <div className="border-t border-slate-800/60 px-5 py-4">{children}</div>}
    </div>
  );
}

// ============================================================
// CODE VIEWER
// ============================================================

function CodeViewer({ code, language, title }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(code).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }, [code]);

  const handleDownload = useCallback(() => {
    const ext = language === "julia" ? ".jl" : ".java";
    const blob = new Blob([code], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `migrated_code${ext}`;
    a.click();
    URL.revokeObjectURL(url);
  }, [code, language]);

  const lines = code.split("\n");

  return (
    <div className="rounded-xl border border-slate-800/70 overflow-hidden bg-[#0a0f1a]">
      <div className="flex items-center justify-between border-b border-slate-800/60 px-4 py-2.5 bg-slate-900/50">
        <div className="flex items-center gap-2">
          <FileCode2 size={14} className="text-cyan-300" />
          <span className="text-xs font-bold text-slate-200">{title}</span>
          <span className="text-[10px] font-mono text-cyan-400/70 bg-cyan-400/10 px-1.5 py-0.5 rounded">{language}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={handleCopy}
            className="flex items-center gap-1 rounded-lg px-2 py-1 text-[10px] font-semibold text-slate-300 transition hover:bg-slate-800 hover:text-white"
            title="Copy code"
          >
            <Copy size={12} />
            {copied ? "Copied!" : "Copy"}
          </button>
          {language === "julia" && (
            <button
              type="button"
              onClick={handleDownload}
              className="flex items-center gap-1 rounded-lg px-2 py-1 text-[10px] font-semibold text-slate-300 transition hover:bg-slate-800 hover:text-white"
              title="Download .jl file"
            >
              <Download size={12} />
              Download
            </button>
          )}
        </div>
      </div>
      <div className="overflow-auto max-h-[500px] p-0">
        <pre className="text-xs leading-6 font-mono text-slate-300 m-0">
          <code>
            {lines.map((line, i) => (
              <div key={i} className="flex hover:bg-slate-800/30 transition-colors">
                <span className="w-12 shrink-0 text-right pr-4 text-slate-600 select-none border-r border-slate-800/50 bg-slate-900/30">{i + 1}</span>
                <span className="pl-4 pr-4 whitespace-pre">{line || " "}</span>
              </div>
            ))}
          </code>
        </pre>
      </div>
    </div>
  );
}

// ============================================================
// MAIN COMPONENT
// ============================================================

export default function MigrationPage() {
  // Upload state
  const [javaCode, setJavaCode] = useState("");
  const [fileName, setFileName] = useState("");
  const fileInputRef = useRef(null);

  // Pipeline state
  const [isRunning, setIsRunning] = useState(false);
  const [currentStep, setCurrentStep] = useState(-1);
  const [completedSteps, setCompletedSteps] = useState({});
  const [error, setError] = useState("");

  // Results
  const [result, setResult] = useState(null);

  // ── File Upload ──────────────────────────────────────────────

  const handleFileSelect = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!file.name.endsWith(".java")) {
      setError("Please upload a .java file.");
      return;
    }

    setError("");

    try {
      const data = await uploadMigrationFile(file);
      setJavaCode(data.java_code);
      setFileName(data.filename);
    } catch (err) {
      // Fallback: read file locally
      try {
        const text = await file.text();
        setJavaCode(text);
        setFileName(file.name);
      } catch {
        setError(err.message || "Failed to read file.");
      }
    }
  };

  const handlePasteCode = () => {
    setFileName("PastedCode.java");
  };

  // ── Run Migration ────────────────────────────────────────────

  const runMigration = async () => {
    if (!javaCode.trim()) {
      setError("Please upload or paste Java code first.");
      return;
    }

    setError("");
    setIsRunning(true);
    setResult(null);
    setCompletedSteps({});
    setCurrentStep(0);

    // Simulate step progression with the actual API call
    const stepInterval = setInterval(() => {
      setCurrentStep((prev) => {
        if (prev < PIPELINE_STEPS.length - 1) {
          setCompletedSteps((cs) => ({ ...cs, [PIPELINE_STEPS[prev].key]: true }));
          return prev + 1;
        }
        return prev;
      });
    }, 3000);

    try {
      const data = await runCompleteMigration(javaCode, fileName);

      clearInterval(stepInterval);

      // Mark all steps completed
      const allCompleted = {};
      PIPELINE_STEPS.forEach((s) => {
        allCompleted[s.key] = true;
      });
      setCompletedSteps(allCompleted);
      setCurrentStep(PIPELINE_STEPS.length);

      if (data.status === "failed" || data.status === "error") {
        setError(data.error || "Migration failed. Please try again.");
        setResult(null);
      } else {
        setResult(data);
      }
    } catch (err) {
      clearInterval(stepInterval);
      setError(err.message || "Migration failed. Please check your code and try again.");
    } finally {
      setIsRunning(false);
    }
  };

  // ── Reset ────────────────────────────────────────────────────

  const resetMigration = () => {
    setJavaCode("");
    setFileName("");
    setResult(null);
    setCompletedSteps({});
    setCurrentStep(-1);
    setError("");
  };

  // ── Render Helpers ───────────────────────────────────────────

  const summary = result?.summary;
  const steps = result?.steps || {};

  return (
    <div className="min-h-[calc(100vh-72px)] grid-bg">
      <main className="mx-auto max-w-7xl px-5 py-8 lg:px-8 lg:py-10">

        {/* ── Header ──────────────────────────────────── */}
        <section className="relative overflow-hidden rounded-3xl border border-purple-400/10 bg-gradient-to-br from-purple-400/[0.08] via-slate-950/60 to-fuchsia-500/[0.08] p-6 shadow-2xl sm:p-8">
          <div className="pointer-events-none absolute -right-24 -top-24 h-64 w-64 rounded-full bg-purple-400/10 blur-3xl" />
          <div className="pointer-events-none absolute -bottom-32 right-1/3 h-72 w-72 rounded-full bg-fuchsia-500/10 blur-3xl" />
          <div className="relative max-w-3xl">
            <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-purple-400/15 bg-purple-400/5 px-3 py-1.5 text-xs font-medium text-purple-200">
              <ArrowRightLeft size={14} />
              Java → Julia Code Migration
            </div>
            <h1 className="text-3xl font-extrabold tracking-tight text-white sm:text-4xl">
              Migrate Java to Julia
            </h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-400 sm:text-base">
              Upload Java source code and automatically convert it to idiomatic Julia with AI-powered analysis, risk detection, error correction, and functional validation.
            </p>
          </div>
        </section>

        {/* ── Upload Section ──────────────────────────── */}
        {!result && (
          <section className="mt-6 grid gap-6 lg:grid-cols-[1fr_340px]">
            <div className="glass rounded-2xl p-6">
              <h2 className="text-sm font-bold text-white mb-4 flex items-center gap-2">
                <Upload size={16} className="text-purple-300" />
                Upload Java Source Code
              </h2>

              {/* File upload area */}
              <div
                className="relative rounded-xl border-2 border-dashed border-slate-700/80 bg-slate-900/40 p-8 text-center transition-colors hover:border-purple-400/40 hover:bg-purple-400/[0.03] cursor-pointer"
                onClick={() => fileInputRef.current?.click()}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".java"
                  className="hidden"
                  onChange={handleFileSelect}
                />
                <div className="grid h-14 w-14 mx-auto place-items-center rounded-2xl bg-purple-400/10 text-purple-300 mb-4">
                  <FileCode2 size={24} />
                </div>
                <p className="text-sm font-semibold text-slate-200">
                  {fileName ? fileName : "Click to upload a .java file"}
                </p>
                <p className="mt-1.5 text-xs text-slate-500">or drag and drop • Max 1MB</p>
              </div>

              {/* Paste code option */}
              <div className="mt-4">
                <p className="text-xs font-semibold text-slate-400 mb-2">Or paste Java code directly:</p>
                <textarea
                  value={javaCode}
                  onChange={(e) => { setJavaCode(e.target.value); handlePasteCode(); }}
                  placeholder={`public class Calculator {\n    public static int add(int a, int b) {\n        return a + b;\n    }\n}`}
                  className="w-full h-48 rounded-xl border border-slate-800/80 bg-[#0a0f1a] p-4 text-xs font-mono text-slate-300 placeholder-slate-600 focus:outline-none focus:border-purple-400/50 resize-none"
                  spellCheck={false}
                />
              </div>

              {/* File info */}
              {fileName && javaCode && (
                <div className="mt-4 flex items-center gap-3 rounded-xl border border-slate-800/70 bg-slate-900/40 px-4 py-3">
                  <FileCode2 size={16} className="text-purple-300" />
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-bold text-white truncate">{fileName}</p>
                    <p className="text-[10px] text-slate-500">{javaCode.split("\n").length} lines • {(new TextEncoder().encode(javaCode).length / 1024).toFixed(1)} KB</p>
                  </div>
                  <button type="button" onClick={resetMigration} className="text-[10px] font-semibold text-rose-300 hover:text-rose-200">Clear</button>
                </div>
              )}

              {/* Error */}
              {error && (
                <div className="mt-4 rounded-xl border border-rose-400/20 bg-rose-400/5 px-4 py-3 text-xs text-rose-200 flex items-start gap-2">
                  <XCircle size={14} className="shrink-0 mt-0.5" />
                  <span>{error}</span>
                </div>
              )}

              {/* Run button */}
              <button
                type="button"
                onClick={runMigration}
                disabled={isRunning || !javaCode.trim()}
                className="mt-5 w-full flex items-center justify-center gap-2.5 rounded-xl bg-gradient-to-r from-purple-500 to-fuchsia-500 px-5 py-3.5 text-sm font-extrabold text-white shadow-lg shadow-purple-500/20 transition hover:-translate-y-0.5 hover:shadow-purple-500/30 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:translate-y-0"
              >
                {isRunning ? (
                  <>
                    <Loader2 size={17} className="animate-spin" />
                    Migrating...
                  </>
                ) : (
                  <>
                    <Play size={17} />
                    Analyze & Migrate
                  </>
                )}
              </button>
            </div>

            {/* Pipeline sidebar */}
            <div className="glass rounded-2xl p-5">
              <div className="flex items-center gap-3 mb-6">
                <div className="grid h-10 w-10 place-items-center rounded-xl bg-purple-400/10 text-purple-300">
                  <ArrowRightLeft size={18} />
                </div>
                <div>
                  <h2 className="text-sm font-bold text-white">Migration Pipeline</h2>
                  <p className="mt-1 text-xs text-slate-500">6-Stage AI Process</p>
                </div>
              </div>

              <div className="space-y-2.5">
                {PIPELINE_STEPS.map((step, index) => {
                  const isCompleted = completedSteps[step.key];
                  const isCurrent = index === currentStep;
                  const Icon = step.icon;

                  return (
                    <div
                      key={step.key}
                      className={`flex items-center gap-3 rounded-xl border px-3 py-2.5 transition-all ${
                        isCompleted
                          ? "border-emerald-500/20 bg-emerald-500/5"
                          : isCurrent
                          ? "border-purple-400/30 bg-purple-400/5 shadow-sm shadow-purple-400/10"
                          : "border-slate-800/80 bg-slate-950/30"
                      }`}
                    >
                      <span className={`grid h-6 w-6 place-items-center rounded-full text-[10px] font-bold ${
                        isCompleted
                          ? "bg-emerald-400/10 text-emerald-300"
                          : isCurrent
                          ? "bg-purple-400/10 text-purple-300"
                          : "bg-slate-800/80 text-slate-500"
                      }`}>
                        {isCompleted ? <CheckCircle2 size={13} /> : index + 1}
                      </span>
                      <span className={`text-xs font-medium flex-1 ${
                        isCompleted ? "text-emerald-300" : isCurrent ? "text-purple-200" : "text-slate-400"
                      }`}>
                        {step.label}
                      </span>
                      {isCurrent && isRunning && (
                        <Loader2 size={13} className="text-purple-400 animate-spin" />
                      )}
                      {isCompleted && (
                        <CheckCircle2 size={13} className="text-emerald-400" />
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          </section>
        )}

        {/* ── Results Section ─────────────────────────── */}
        {result && (
          <section className="mt-6 space-y-6">

            {/* Summary bar */}
            {summary && (
              <div className="glass rounded-2xl p-5">
                <h2 className="text-sm font-bold text-white mb-4 flex items-center gap-2">
                  <BarChart3 size={16} className="text-purple-300" />
                  Migration Summary
                </h2>
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                  {[
                    { label: "Source → Target", value: `${summary.source_language} → ${summary.target_language}`, color: "text-purple-300" },
                    { label: "Risk Level", value: summary.risk_level, color: summary.risk_level === "HIGH" ? "text-rose-400" : summary.risk_level === "MEDIUM" ? "text-amber-400" : "text-emerald-400" },
                    { label: "Errors", value: `${summary.errors_detected} found / ${summary.errors_corrected} fixed`, color: summary.errors_detected > 0 ? "text-amber-400" : "text-emerald-400" },
                    { label: "Validation", value: summary.validation_status, color: summary.validation_status === "VALIDATED" ? "text-emerald-400" : summary.validation_status === "FAILED" ? "text-rose-400" : "text-amber-400" },
                  ].map(({ label, value, color }) => (
                    <div key={label} className="rounded-xl border border-slate-800/70 bg-slate-900/40 p-4">
                      <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">{label}</p>
                      <p className={`mt-1.5 text-sm font-extrabold ${color}`}>{value}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Side-by-side code */}
            <div className="grid gap-4 lg:grid-cols-2">
              <CodeViewer code={result.java_code || javaCode} language="java" title="Original Java Code" />
              <CodeViewer code={result.julia_code || ""} language="julia" title="Migrated Julia Code" />
            </div>
            
            {/* Show error if migration failed but Julia code exists */}
            {result.status === "failed" && result.julia_code && (
              <div className="rounded-xl border border-amber-400/20 bg-amber-400/5 px-4 py-3 text-xs text-amber-200 flex items-start gap-2">
                <AlertTriangle size={14} className="shrink-0 mt-0.5" />
                <span>Migration encountered errors, but partial Julia code is available above. Review the error details below.</span>
              </div>
            )}

            {/* Detailed reports */}
            <div className="space-y-3">

              {/* Migration Analysis */}
              {steps.analysis?.result && (
                <CollapsibleSection title="Migration Analysis" icon={BarChart3} badge={`${steps.analysis.result.classes || 0} classes • ${steps.analysis.result.methods || 0} methods`}>
                  <div className="grid gap-2 sm:grid-cols-3 lg:grid-cols-4">
                    {[
                      ["Lines of Code", steps.analysis.result.lines_of_code],
                      ["Classes", steps.analysis.result.classes],
                      ["Interfaces", steps.analysis.result.interfaces],
                      ["Methods", steps.analysis.result.methods],
                      ["Constructors", steps.analysis.result.constructors],
                      ["Loops", steps.analysis.result.loops],
                      ["Conditionals", steps.analysis.result.conditional_blocks],
                      ["Exception Handling", steps.analysis.result.exception_handling],
                      ["Collections", steps.analysis.result.collections],
                      ["Inheritance", steps.analysis.result.inheritance],
                      ["Static Members", steps.analysis.result.static_members],
                      ["Imports", steps.analysis.result.imports],
                    ].map(([label, value]) => (
                      <div key={label} className="rounded-lg border border-slate-800/60 bg-slate-900/30 px-3 py-2">
                        <p className="text-[10px] text-slate-500">{label}</p>
                        <p className="text-sm font-bold text-white">{value ?? 0}</p>
                      </div>
                    ))}
                  </div>
                  {steps.analysis.result.migration_concerns?.length > 0 && (
                    <div className="mt-4">
                      <p className="text-xs font-bold text-slate-300 mb-2">Migration Concerns:</p>
                      <ul className="space-y-1.5">
                        {steps.analysis.result.migration_concerns.map((concern, i) => (
                          <li key={i} className="flex items-start gap-2 text-xs text-slate-400">
                            <AlertTriangle size={12} className="text-amber-400 shrink-0 mt-0.5" />
                            {concern}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </CollapsibleSection>
              )}

              {/* Conversion Notes */}
              {steps.conversion?.result && (
                <CollapsibleSection title="Conversion Details" icon={ArrowRightLeft} badge={steps.conversion.status === "failed" ? "Failed" : "Completed"}>
                  {steps.conversion.status === "failed" && steps.conversion.result.error && (
                    <div className="mb-3 rounded-xl border border-rose-400/20 bg-rose-400/5 px-4 py-3 text-xs text-rose-200 flex items-start gap-2">
                      <XCircle size={14} className="shrink-0 mt-0.5" />
                      <span>{steps.conversion.result.error}</span>
                    </div>
                  )}
                  {steps.conversion.result.conversion_notes?.length > 0 && (
                    <div className="mb-3">
                      <p className="text-xs font-bold text-slate-300 mb-2">Conversion Notes:</p>
                      <ul className="space-y-1.5">
                        {steps.conversion.result.conversion_notes.map((note, i) => (
                          <li key={i} className="flex items-start gap-2 text-xs text-slate-400">
                            <Info size={12} className="text-cyan-400 shrink-0 mt-0.5" />
                            {note}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {steps.conversion.result.unsupported_features?.length > 0 && (
                    <div>
                      <p className="text-xs font-bold text-slate-300 mb-2">Unsupported Features:</p>
                      <ul className="space-y-1.5">
                        {steps.conversion.result.unsupported_features.map((feat, i) => (
                          <li key={i} className="flex items-start gap-2 text-xs text-rose-300">
                            <XCircle size={12} className="shrink-0 mt-0.5" />
                            {feat}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {!steps.conversion.result.conversion_notes?.length && !steps.conversion.result.unsupported_features?.length && !steps.conversion.result.error && (
                    <p className="text-xs text-slate-400">No conversion details available.</p>
                  )}
                </CollapsibleSection>
              )}

              {/* Risk Analysis */}
              {steps.risk_analysis?.result && (
                <CollapsibleSection
                  title="Migration Risks"
                  icon={Shield}
                  badge={`${steps.risk_analysis.result.summary?.total || 0} risks • ${steps.risk_analysis.result.summary?.overall_risk_level || "N/A"}`}
                >
                  {steps.risk_analysis.result.risks?.length > 0 ? (
                    <div className="space-y-3">
                      {steps.risk_analysis.result.risks.map((risk, i) => (
                        <div key={i} className="rounded-xl border border-slate-800/60 bg-slate-900/30 p-4">
                          <div className="flex items-start justify-between gap-3 mb-2">
                            <p className="text-xs font-bold text-white">{risk.risk}</p>
                            <SeverityBadge severity={risk.severity} />
                          </div>
                          <p className="text-xs text-slate-400 mb-2">{risk.description}</p>
                          {risk.affected_code && (
                            <p className="text-[10px] text-slate-500 mb-1"><span className="text-slate-400 font-semibold">Affected:</span> {risk.affected_code}</p>
                          )}
                          {risk.suggested_resolution && (
                            <p className="text-[10px] text-emerald-400/80"><span className="font-semibold">Resolution:</span> {risk.suggested_resolution}</p>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-slate-400">No migration risks detected.</p>
                  )}
                </CollapsibleSection>
              )}

              {/* Error Detection */}
              {steps.error_detection?.result && (
                <CollapsibleSection
                  title="Error Report"
                  icon={Bug}
                  badge={`${steps.error_detection.result.summary?.total || 0} issues`}
                >
                  {steps.error_detection.result.errors?.length > 0 ? (
                    <div className="space-y-2.5">
                      {steps.error_detection.result.errors.map((err, i) => (
                        <div key={i} className="rounded-xl border border-slate-800/60 bg-slate-900/30 p-3.5 flex items-start gap-3">
                          <div className="shrink-0 mt-0.5">
                            {err.type === "ERROR" ? (
                              <XCircle size={14} className="text-rose-400" />
                            ) : (
                              <AlertTriangle size={14} className="text-amber-400" />
                            )}
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <span className="text-[10px] font-bold text-slate-300">{err.type}</span>
                              {err.line > 0 && <span className="text-[10px] font-mono text-cyan-400/70">Line {err.line}</span>}
                              <SeverityBadge severity={err.severity} />
                            </div>
                            <p className="text-xs text-slate-400">{err.issue}</p>
                            {err.code_snippet && (
                              <pre className="mt-1.5 text-[10px] font-mono text-slate-500 bg-slate-950/60 rounded px-2 py-1 overflow-x-auto">{err.code_snippet}</pre>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-emerald-400 flex items-center gap-2">
                      <CheckCircle2 size={14} />
                      No errors detected in the generated Julia code.
                    </p>
                  )}
                </CollapsibleSection>
              )}

              {/* Error Corrections */}
              {steps.error_correction && steps.error_correction.iterations > 0 && (
                <CollapsibleSection
                  title="Correction Report"
                  icon={Wrench}
                  badge={`${steps.error_correction.iterations} iterations`}
                >
                  <div className="space-y-3">
                    {steps.error_correction.corrections?.map((iter, i) => (
                      <div key={i} className="rounded-xl border border-slate-800/60 bg-slate-900/30 p-4">
                        <p className="text-xs font-bold text-white mb-2">Iteration {iter.iteration}</p>
                        {iter.corrections?.length > 0 ? (
                          <div className="space-y-2">
                            {iter.corrections.map((c, j) => (
                              <div key={j} className="text-xs text-slate-400 border-l-2 border-emerald-500/30 pl-3">
                                {c.reason && <p className="text-slate-300 font-medium">{c.reason}</p>}
                                {c.original && (
                                  <pre className="mt-1 text-[10px] font-mono text-rose-300/70 line-through">{c.original}</pre>
                                )}
                                {c.corrected && (
                                  <pre className="text-[10px] font-mono text-emerald-300/70">{c.corrected}</pre>
                                )}
                              </div>
                            ))}
                          </div>
                        ) : (
                          <p className="text-xs text-slate-500">Corrections applied (details not available).</p>
                        )}
                      </div>
                    ))}
                  </div>
                </CollapsibleSection>
              )}

              {/* Validation Report */}
              {steps.validation?.result && (
                <CollapsibleSection
                  title="Validation Report"
                  icon={ClipboardCheck}
                  defaultOpen
                  badge={steps.validation.result.status}
                >
                  <div className="space-y-4">
                    {/* Status */}
                    <div className={`rounded-xl border p-4 ${
                      steps.validation.result.status === "VALIDATED"
                        ? "border-emerald-500/20 bg-emerald-500/5"
                        : steps.validation.result.status === "FAILED"
                        ? "border-rose-500/20 bg-rose-500/5"
                        : "border-amber-500/20 bg-amber-500/5"
                    }`}>
                      <div className="flex items-center gap-2 mb-1">
                        {steps.validation.result.status === "VALIDATED" ? (
                          <CheckCircle2 size={16} className="text-emerald-400" />
                        ) : steps.validation.result.status === "FAILED" ? (
                          <XCircle size={16} className="text-rose-400" />
                        ) : (
                          <AlertTriangle size={16} className="text-amber-400" />
                        )}
                        <span className="text-sm font-bold text-white">{steps.validation.result.status}</span>
                        {steps.validation.result.overall_confidence > 0 && (
                          <span className="ml-auto text-xs font-bold text-slate-400">{steps.validation.result.overall_confidence}% confidence</span>
                        )}
                      </div>
                      <p className="text-xs text-slate-400">{steps.validation.result.status_description}</p>
                    </div>

                    {/* Behavior comparison */}
                    {(steps.validation.result.java_behavior || steps.validation.result.julia_behavior) && (
                      <div className="grid gap-3 sm:grid-cols-2">
                        <div className="rounded-xl border border-slate-800/60 bg-slate-900/30 p-3.5">
                          <p className="text-[10px] font-bold text-orange-300 uppercase tracking-wider mb-1">Java Behavior</p>
                          <p className="text-xs text-slate-400">{steps.validation.result.java_behavior}</p>
                        </div>
                        <div className="rounded-xl border border-slate-800/60 bg-slate-900/30 p-3.5">
                          <p className="text-[10px] font-bold text-purple-300 uppercase tracking-wider mb-1">Julia Behavior</p>
                          <p className="text-xs text-slate-400">{steps.validation.result.julia_behavior}</p>
                        </div>
                      </div>
                    )}

                    {/* Test cases */}
                    {steps.validation.result.test_cases?.length > 0 && (
                      <div>
                        <p className="text-xs font-bold text-slate-300 mb-2">Test Cases:</p>
                        <div className="space-y-2">
                          {steps.validation.result.test_cases.map((tc, i) => (
                            <div key={i} className="flex items-start gap-3 rounded-lg border border-slate-800/60 bg-slate-900/30 p-3">
                              {tc.match ? (
                                <CheckCircle2 size={14} className="text-emerald-400 shrink-0 mt-0.5" />
                              ) : (
                                <XCircle size={14} className="text-rose-400 shrink-0 mt-0.5" />
                              )}
                              <div className="flex-1 min-w-0">
                                <p className="text-xs font-semibold text-white">{tc.name}</p>
                                <p className="text-[10px] text-slate-500 mt-0.5">Input: {tc.input}</p>
                                <p className="text-[10px] text-slate-500">Expected: {tc.expected_java_output}</p>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Functional comparison */}
                    {steps.validation.result.functional_comparison?.length > 0 && (
                      <div>
                        <p className="text-xs font-bold text-slate-300 mb-2">Functional Comparison:</p>
                        <div className="overflow-x-auto">
                          <table className="w-full text-xs">
                            <thead>
                              <tr className="border-b border-slate-800/60">
                                <th className="text-left py-2 px-3 text-slate-500 font-semibold">Feature</th>
                                <th className="text-left py-2 px-3 text-slate-500 font-semibold">Java</th>
                                <th className="text-left py-2 px-3 text-slate-500 font-semibold">Julia</th>
                                <th className="text-center py-2 px-3 text-slate-500 font-semibold">Match</th>
                              </tr>
                            </thead>
                            <tbody>
                              {steps.validation.result.functional_comparison.map((fc, i) => (
                                <tr key={i} className="border-b border-slate-800/40">
                                  <td className="py-2 px-3 text-slate-300 font-medium">{fc.feature}</td>
                                  <td className="py-2 px-3 text-slate-400">{fc.java_behavior}</td>
                                  <td className="py-2 px-3 text-slate-400">{fc.julia_behavior}</td>
                                  <td className="py-2 px-3 text-center">
                                    {fc.match ? (
                                      <CheckCircle2 size={14} className="text-emerald-400 mx-auto" />
                                    ) : (
                                      <XCircle size={14} className="text-rose-400 mx-auto" />
                                    )}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                    )}
                  </div>
                </CollapsibleSection>
              )}
            </div>

            {/* Reset / New Migration button */}
            <div className="flex justify-center pt-2 pb-6">
              <button
                type="button"
                onClick={resetMigration}
                className="flex items-center gap-2 rounded-xl border border-purple-400/30 bg-purple-400/10 px-6 py-3 text-sm font-bold text-purple-200 transition hover:bg-purple-400/20"
              >
                <RefreshCw size={16} />
                New Migration
              </button>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
