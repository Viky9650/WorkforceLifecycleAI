"use client";

import { useEffect, useMemo, useState } from "react";

type TraceItem = { agent: string; status: "ok" | "error" | string; detail?: string };
type ApiResp = any;

type CurrentUser = {
  name: string;
  email: string;
  role: "employee" | "hr" | "admin";
};

type DashboardEmployee = {
  id: number;
  name: string;
  email: string;
  manager_email: string;
  role: string;
  department?: string | null;
  employment_status: "active" | "inactive";
  lifecycle_status: "onboarded" | "offboarded";
  created_at: string;
  updated_at: string;
  access: Record<string, string>;
  access_summary?: {
    total: number;
    granted: number;
    revoked: number;
  };
};

type DashboardResp = {
  summary?: {
    total: number;
    active: number;
    inactive: number;
  };
  pagination?: {
    page: number;
    page_size: number;
    total_filtered: number;
    total_pages: number;
  };
  employees?: DashboardEmployee[];
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "/api";
const DEV_USER_EMAIL = "hr@company.com";

function cx(...classes: (string | false | null | undefined)[]) {
  return classes.filter(Boolean).join(" ");
}

function Pill({
  children,
  tone = "neutral",
}: {
  children: React.ReactNode;
  tone?: "neutral" | "primary" | "success" | "danger";
}) {
  const tones: Record<string, string> = {
    neutral: "border-slate-200 bg-white text-slate-700",
    primary: "border-teal-200 bg-teal-50 text-teal-800",
    success: "border-emerald-200 bg-emerald-50 text-emerald-800",
    danger: "border-rose-200 bg-rose-50 text-rose-800",
  };
  return (
    <span className={cx("inline-flex items-center rounded-full border px-2.5 py-1 text-xs", tones[tone])}>
      {children}
    </span>
  );
}

function Button({
  children,
  onClick,
  disabled,
  variant = "secondary",
}: {
  children: React.ReactNode;
  onClick?: () => void;
  disabled?: boolean;
  variant?: "primary" | "secondary" | "danger";
}) {
  const styles =
    variant === "primary"
      ? "bg-teal-600 text-white hover:bg-teal-700 border-teal-600"
      : variant === "danger"
      ? "bg-rose-600 text-white hover:bg-rose-700 border-rose-600"
      : "bg-white text-slate-800 hover:bg-slate-50 border-slate-200";

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={cx(
        "inline-flex items-center justify-center gap-2 rounded-xl border px-4 py-2 text-sm font-medium shadow-sm transition disabled:opacity-50 disabled:cursor-not-allowed",
        styles
      )}
    >
      {children}
    </button>
  );
}

function Card({
  title,
  subtitle,
  children,
  right,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  right?: React.ReactNode;
}) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white/90 backdrop-blur shadow-sm">
      <div className="flex items-start justify-between gap-3 border-b border-slate-100 p-4">
        <div>
          <div className="text-sm font-semibold text-slate-900">{title}</div>
          {subtitle ? <div className="mt-1 text-xs text-slate-500">{subtitle}</div> : null}
        </div>
        {right ? <div className="shrink-0">{right}</div> : null}
      </div>
      <div className="p-4">{children}</div>
    </section>
  );
}

function StatusDot({ status }: { status: string }) {
  const ok = status === "ok";
  return (
    <span className="inline-flex items-center gap-2 text-xs">
      <span className={cx("h-2.5 w-2.5 rounded-full", ok ? "bg-emerald-500" : "bg-rose-500")} />
      <span className={cx("font-medium", ok ? "text-emerald-700" : "text-rose-700")}>{ok ? "ok" : status}</span>
    </span>
  );
}

function Timeline({ trace }: { trace?: TraceItem[] }) {
  if (!trace?.length) return <div className="text-xs text-slate-500">No trace yet.</div>;
  return (
    <div className="space-y-3">
      {trace.map((t, i) => (
        <div key={i} className="flex gap-3">
          <div className="mt-1">
            <StatusDot status={t.status} />
          </div>
          <div className="min-w-0 flex-1">
            <div className="text-sm font-medium text-slate-900">{t.agent}</div>
            {t.detail ? <div className="mt-1 text-xs text-slate-500">{t.detail}</div> : null}
          </div>
        </div>
      ))}
    </div>
  );
}

function prettyRunLabel(runPath: string) {
  const file = runPath.split("/").pop() || runPath;
  return file.replace(".json", "").replaceAll("_", " ");
}

export default function Page() {
  const [mode, setMode] = useState<"assistant" | "lifecycle">("assistant");

  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [dashboard, setDashboard] = useState<DashboardResp | null>(null);
  const [dashboardLoading, setDashboardLoading] = useState(false);

  const [name, setName] = useState("Viky");
  const [email, setEmail] = useState("viky@company.com");
  const [managerEmail, setManagerEmail] = useState("manager@company.com");
  const [role, setRole] = useState("SRE");

  const [question, setQuestion] = useState("What access is required for the application?");

  const [onboardLoading, setOnboardLoading] = useState(false);
  const [offboardLoading, setOffboardLoading] = useState(false);

  const [chatInput, setChatInput] = useState("Where is onboarding document?");
  const [chatLoading, setChatLoading] = useState(false);

  const [resp, setResp] = useState<ApiResp | null>(null);
  const [runs, setRuns] = useState<string[]>([]);
  const [selectedRun, setSelectedRun] = useState<string | null>(null);
  const [runLoading, setRunLoading] = useState(false);

  const [error, setError] = useState<string | null>(null);

  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | "active" | "inactive">("all");
  const [roleFilter, setRoleFilter] = useState("all");
  const [roleOptions, setRoleOptions] = useState<string[]>([]);
  const [page, setPage] = useState(1);
  const pageSize = 10;

  const [selectedEmployee, setSelectedEmployee] = useState<DashboardEmployee | null>(null);

  const [chatMsgs, setChatMsgs] = useState<
    { who: "user" | "assistant" | "event"; text: string; meta?: any }[]
  >([{ who: "assistant", text: "Hi 👋 Ask onboarding questions. Policy questions use access policy; knowledge questions use RAG docs." }]);

  async function refreshRuns() {
    try {
      const r = await fetch(`${API_BASE}/runs`);
      if (!r.ok) return;
      const data = await r.json();
      setRuns(data?.runs || []);
    } catch {}
  }

  async function loadMe() {
    try {
      const r = await fetch(`${API_BASE}/me`, {
        headers: {
          "x-user-email": DEV_USER_EMAIL,
        },
      });
      if (!r.ok) throw new Error(await r.text());
      const data = await r.json();
      setCurrentUser(data);
    } catch (e) {
      console.error("Failed to load current user", e);
    }
  }

  async function loadRoles() {
    try {
      const r = await fetch(`${API_BASE}/employees/roles`);
      if (!r.ok) throw new Error(await r.text());
      const data = await r.json();
      setRoleOptions(data?.roles || []);
    } catch (e) {
      console.error("Failed to load roles", e);
    }
  }

  async function loadDashboard() {
    setDashboardLoading(true);
    try {
      const params = new URLSearchParams({
        page: String(page),
        page_size: String(pageSize),
      });

      if (searchTerm.trim()) params.set("search", searchTerm.trim());
      if (statusFilter !== "all") params.set("status", statusFilter);
      if (roleFilter !== "all") params.set("role", roleFilter);

      const r = await fetch(`${API_BASE}/employees/dashboard?${params.toString()}`);
      if (!r.ok) throw new Error(await r.text());
      const data = await r.json();
      setDashboard(data);
    } catch (e) {
      console.error("Failed to load dashboard", e);
    } finally {
      setDashboardLoading(false);
    }
  }

  useEffect(() => {
    refreshRuns();
    loadMe();
    loadRoles();
  }, []);

  useEffect(() => {
    loadDashboard();
  }, [page, pageSize, searchTerm, statusFilter, roleFilter]);

  useEffect(() => {
    if (currentUser?.role === "employee" && mode === "lifecycle") {
      setMode("assistant");
    }
  }, [currentUser, mode]);

  async function loadRun(runPath: string) {
    setRunLoading(true);
    setError(null);
    setSelectedRun(runPath);

    try {
      const r = await fetch(`${API_BASE}/run?path=${encodeURIComponent(runPath)}`);
      if (!r.ok) throw new Error(await r.text());
      const data = await r.json();
      setResp(data);
      setChatMsgs((m) => [...m, { who: "event", text: `Loaded run: ${prettyRunLabel(runPath)}` }]);
    } catch (e: any) {
      setError(e?.message || "Could not load run details");
    } finally {
      setRunLoading(false);
    }
  }

  const trace = resp?.trace as TraceItem[] | undefined;
  const access = resp?.access;
  const chat = resp?.chat;
  const notifications = resp?.notifications || {};

  const latestSources: string[] = useMemo(() => {
    const s = chat?.sources || resp?.rag_sources?.primary || [];
    return Array.isArray(s) ? s : [];
  }, [chat?.sources, resp?.rag_sources]);

  async function callLifecycle(endpoint: "/onboard" | "/offboard") {
    setError(null);

    if (endpoint === "/onboard") setOnboardLoading(true);
    if (endpoint === "/offboard") setOffboardLoading(true);

    try {
      const payload =
        endpoint === "/offboard"
          ? {
              name,
              email,
              manager_email: managerEmail,
              role,
              question,
              kt_notes: "KT: runbooks, dashboards, incident ownership, deployment steps.",
            }
          : { name, email, manager_email: managerEmail, role, question };

      const r = await fetch(`${API_BASE}${endpoint}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-user-email": currentUser?.email || DEV_USER_EMAIL,
        },
        body: JSON.stringify(payload),
      });

      if (!r.ok) throw new Error(await r.text());

      const data = await r.json();
      setResp(data);
      await refreshRuns();
      await loadDashboard();

      setChatMsgs((m) => [
        ...m,
        { who: "event", text: endpoint === "/onboard" ? "Lifecycle: Onboard completed" : "Lifecycle: Offboard completed" },
      ]);
    } catch (e: any) {
      setError(e?.message || "Request failed");
    } finally {
      setOnboardLoading(false);
      setOffboardLoading(false);
    }
  }

  async function sendChat() {
    const q = chatInput.trim();
    if (!q) return;

    setChatLoading(true);
    setError(null);
    setChatMsgs((m) => [...m, { who: "user", text: q }]);
    setChatInput("");

    try {
      const r = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name,
          email,
          manager_email: managerEmail,
          role,
          question: q,
        }),
      });

      if (!r.ok) throw new Error(await r.text());

      const data = await r.json();
      setResp(data);

      const ans = data?.chat?.answer || "(no answer)";
      setChatMsgs((m) => [...m, { who: "assistant", text: ans, meta: data }]);
    } catch (e: any) {
      setError(e?.message || "Chat failed");
      setChatMsgs((m) => [...m, { who: "assistant", text: "⚠️ Chat failed. Please check API and credentials." }]);
    } finally {
      setChatLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-gradient-to-b from-slate-50 via-slate-50 to-sky-50">
      <div className="border-b border-slate-200/70 bg-white/70 backdrop-blur">
        <div className="mx-auto max-w-7xl px-4 py-4">
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-2xl bg-gradient-to-br from-teal-600 to-sky-500 shadow-sm" />
              <div>
                <div className="text-lg font-semibold text-slate-900">WorkforceLifecycleAI</div>
                <div className="text-xs text-slate-500">From onboarding to offboarding — in one intelligent orbit.</div>
              </div>
            </div>

            <div className="flex items-center gap-2 flex-wrap">
              {currentUser ? (
                <Pill tone={currentUser.role === "employee" ? "neutral" : "success"}>
                  {currentUser.name} • {currentUser.role}
                </Pill>
              ) : null}

              <Pill tone="primary">Runs: {runs.length}</Pill>

              <div className="inline-flex rounded-2xl border border-slate-200 bg-white/70 p-1 shadow-sm">
                <button
                  onClick={() => setMode("assistant")}
                  className={cx(
                    "rounded-xl px-4 py-2 text-sm font-semibold transition-all",
                    mode === "assistant"
                      ? "bg-gradient-to-r from-cyan-500 to-sky-500 text-white shadow-md"
                      : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                  )}
                >
                  Assistant
                </button>

                {(currentUser?.role === "admin" || currentUser?.role === "hr") && (
                  <button
                    onClick={() => setMode("lifecycle")}
                    className={cx(
                      "rounded-xl px-4 py-2 text-sm font-semibold transition-all",
                      mode === "lifecycle"
                        ? "bg-gradient-to-r from-violet-500 to-fuchsia-500 text-white shadow-md"
                        : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                    )}
                  >
                    Lifecycle
                  </button>
                )}
              </div>
            </div>
          </div>

          {error ? (
            <div className="mt-3 rounded-2xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">
              {error}
            </div>
          ) : null}
        </div>
      </div>

      <div className="mx-auto max-w-7xl px-4 py-6">
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-12">
          <div className="xl:col-span-3 space-y-4">
            <Card title="Employee Profile" subtitle="Used for chat + lifecycle runs">
              <div className="space-y-3">
                <div>
                  <div className="mb-1 text-xs font-medium text-slate-700">Employee Name</div>
                  <input
                    className="w-full rounded-xl border border-slate-200 bg-white p-2 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                  />
                </div>

                <div>
                  <div className="mb-1 text-xs font-medium text-slate-700">Employee Email</div>
                  <input
                    className="w-full rounded-xl border border-slate-200 bg-white p-2 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                  />
                </div>

                <div>
                  <div className="mb-1 text-xs font-medium text-slate-700">Manager Email</div>
                  <input
                    className="w-full rounded-xl border border-slate-200 bg-white p-2 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
                    value={managerEmail}
                    onChange={(e) => setManagerEmail(e.target.value)}
                  />
                </div>

                <div>
                  <div className="mb-1 text-xs font-medium text-slate-700">Role</div>
                  <input
                    className="w-full rounded-xl border border-slate-200 bg-white p-2 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
                    value={role}
                    onChange={(e) => setRole(e.target.value)}
                  />
                </div>

                {mode === "lifecycle" && (currentUser?.role === "admin" || currentUser?.role === "hr") ? (
                  <div className="grid grid-cols-2 gap-2 pt-2">
                    <Button
                      variant="primary"
                      disabled={onboardLoading || offboardLoading}
                      onClick={() => callLifecycle("/onboard")}
                    >
                      {onboardLoading ? "Running…" : "Onboard"}
                    </Button>
                    <Button
                      variant="danger"
                      disabled={onboardLoading || offboardLoading}
                      onClick={() => callLifecycle("/offboard")}
                    >
                      {offboardLoading ? "Running…" : "Offboard"}
                    </Button>
                  </div>
                ) : (
                  <div className="pt-2 text-xs text-slate-500">
                    {currentUser?.role === "employee"
                      ? "Employees can use chat and view dashboard data. Lifecycle actions are restricted to HR/Admin."
                      : "Assistant mode won’t provision access. Switch to Lifecycle for onboarding/offboarding."}
                  </div>
                )}
              </div>
            </Card>

            <Card
              title="Runs"
              subtitle="Audit-ready history"
              right={runLoading ? <Pill tone="primary">Loading…</Pill> : <Pill>Click to load</Pill>}
            >
              <div className="max-h-[260px] space-y-2 overflow-auto pr-1">
                {runs.length === 0 ? (
                  <div className="text-xs text-slate-500">No runs yet.</div>
                ) : (
                  runs.slice().reverse().map((r: string, idx: number) => (
                    <button
                      key={idx}
                      onClick={() => loadRun(r)}
                      className={cx(
                        "w-full rounded-xl border px-3 py-2 text-left text-xs transition",
                        selectedRun === r
                          ? "border-teal-200 bg-teal-50 text-teal-900"
                          : "border-slate-200 bg-white hover:bg-slate-50 text-slate-700"
                      )}
                      title={r}
                    >
                      {prettyRunLabel(r)}
                    </button>
                  ))
                )}
              </div>
            </Card>

            <Card title="Agent Trace" subtitle="What ran and why">
              <Timeline trace={trace} />
            </Card>
          </div>

          <div className="xl:col-span-5 space-y-4">
            <Card
              title={mode === "assistant" ? "AI Chat" : "Lifecycle Notes"}
              subtitle={mode === "assistant" ? "Calm UI • fast answers • safe policy rules" : "Runs multi-agent orchestration + tools + audit"}
              right={
                mode === "assistant" ? (
                  <span className="inline-flex items-center rounded-full border border-cyan-200 bg-cyan-50 px-2.5 py-1 text-xs font-medium text-cyan-700">
                    Assistant
                  </span>
                ) : (
                  <span className="inline-flex items-center rounded-full border border-fuchsia-200 bg-fuchsia-50 px-2.5 py-1 text-xs font-medium text-fuchsia-700">
                    Lifecycle
                  </span>
                )
              }
            >
              {mode === "assistant" ? (
                <div className="flex flex-col gap-3">
                  <div className="h-[480px] overflow-auto rounded-2xl border border-slate-200 bg-white p-4">
                    <div className="space-y-3">
                      {chatMsgs.map((m, i) => {
                        if (m.who === "event") {
                          return (
                            <div key={i} className="flex justify-center">
                              <div className="max-w-[92%] rounded-2xl border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-700 whitespace-pre-wrap">
                                {m.text}
                              </div>
                            </div>
                          );
                        }
                        const isUser = m.who === "user";
                        return (
                          <div key={i} className={cx("flex", isUser ? "justify-end" : "justify-start")}>
                            <div
                              className={cx(
                                "max-w-[85%] rounded-2xl px-3 py-2 text-sm shadow-sm",
                                isUser
                                  ? "bg-gradient-to-br from-teal-600 to-sky-500 text-white"
                                  : "bg-white text-slate-900 border border-slate-200"
                              )}
                            >
                              <div className="whitespace-pre-wrap">{m.text}</div>
                            </div>
                          </div>
                        );
                      })}
                      {chatLoading ? (
                        <div className="flex justify-start">
                          <div className="rounded-2xl border border-cyan-200 bg-cyan-50 px-3 py-2 text-sm text-cyan-700">
                            Thinking…
                          </div>
                        </div>
                      ) : null}
                    </div>
                  </div>

                  <div className="flex gap-2">
                    <input
                      className="flex-1 rounded-xl border border-slate-200 bg-white p-3 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-500"
                      placeholder="Ask a question…"
                      value={chatInput}
                      onChange={(e) => setChatInput(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") sendChat();
                      }}
                    />
                    <Button variant="primary" disabled={chatLoading} onClick={sendChat}>
                      Send
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="space-y-3">
                  <div>
                    <div className="mb-1 text-xs font-medium text-slate-700">Question / Notes</div>
                    <textarea
                      className="w-full min-h-[220px] rounded-xl border border-slate-200 bg-white p-3 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500"
                      value={question}
                      onChange={(e) => setQuestion(e.target.value)}
                    />
                  </div>
                </div>
              )}
            </Card>

            <Card title="Latest Answer" subtitle="Most recent assistant output">
              <div className="whitespace-pre-wrap text-sm text-slate-900">{chat?.answer || "(no answer yet)"}</div>
              {latestSources?.length ? (
                <div className="mt-3 flex flex-wrap gap-2">
                  {latestSources.map((s: string, i: number) => (
                    <Pill key={i} tone="primary">
                      {s}
                    </Pill>
                  ))}
                </div>
              ) : (
                <div className="mt-2 text-xs text-slate-500">No sources yet.</div>
              )}
            </Card>

            <Card title="Employee Access Details" subtitle="Full per-system view for selected employee">
              {!selectedEmployee ? (
                <div className="text-sm text-slate-500">Select an employee from the table.</div>
              ) : (
                <div className="space-y-3">
                  <div className="text-sm font-medium text-slate-900">
                    {selectedEmployee.name} • {selectedEmployee.role}
                  </div>

                  <div className="grid grid-cols-1 gap-2">
                    {Object.entries(selectedEmployee.access || {}).map(([system, value]) => (
                      <div
                        key={system}
                        className="flex items-center justify-between rounded-xl border border-slate-200 bg-slate-50 px-3 py-2"
                      >
                        <span className="text-sm text-slate-700">{system}</span>
                        <span className="text-sm font-medium text-slate-900">{String(value)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </Card>
          </div>

          <div className="xl:col-span-4 space-y-4">
            <Card title="Employee Dashboard" subtitle="Active vs inactive workforce">
              {dashboardLoading ? (
                <div className="text-sm text-slate-500">Loading dashboard…</div>
              ) : (
                <div className="space-y-4">
                  <div className="grid grid-cols-3 gap-3">
                    <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                      <div className="text-xs text-slate-500">Total</div>
                      <div className="text-xl font-semibold text-slate-900">
                        {dashboard?.summary?.total ?? 0}
                      </div>
                    </div>
                    <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-3">
                      <div className="text-xs text-emerald-700">Active</div>
                      <div className="text-xl font-semibold text-emerald-800">
                        {dashboard?.summary?.active ?? 0}
                      </div>
                    </div>
                    <div className="rounded-xl border border-rose-200 bg-rose-50 p-3">
                      <div className="text-xs text-rose-700">Inactive</div>
                      <div className="text-xl font-semibold text-rose-800">
                        {dashboard?.summary?.inactive ?? 0}
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </Card>

            <Card title="Employees" subtitle="Compact view with pagination">
              <div className="space-y-3">
                <div className="flex flex-col gap-2 md:flex-row md:items-center">
                  <input
                    className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm"
                    placeholder="Search name, email, manager..."
                    value={searchTerm}
                    onChange={(e) => {
                      setPage(1);
                      setSearchTerm(e.target.value);
                    }}
                  />

                  <select
                    className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm"
                    value={statusFilter}
                    onChange={(e) => {
                      setPage(1);
                      setStatusFilter(e.target.value as "all" | "active" | "inactive");
                    }}
                  >
                    <option value="all">All Status</option>
                    <option value="active">Active</option>
                    <option value="inactive">Inactive</option>
                  </select>

                  <select
                    className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm"
                    value={roleFilter}
                    onChange={(e) => {
                      setPage(1);
                      setRoleFilter(e.target.value);
                    }}
                  >
                    <option value="all">All Roles</option>
                    {roleOptions.map((roleOption) => (
                      <option key={roleOption} value={roleOption}>
                        {roleOption}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="overflow-x-auto rounded-xl border border-slate-200">
                  <table className="min-w-full text-sm">
                    <thead className="sticky top-0 bg-slate-50">
                      <tr className="border-b border-slate-200 text-left text-slate-500">
                        <th className="px-3 py-2">Name</th>
                        <th className="px-3 py-2">Email</th>
                        <th className="px-3 py-2">Role</th>
                        <th className="px-3 py-2">Status</th>
                        <th className="px-3 py-2">Access</th>
                        <th className="px-3 py-2">Updated</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(dashboard?.employees || []).map((emp) => (
                        <tr
                          key={emp.id}
                          className="cursor-pointer border-b border-slate-100 hover:bg-slate-50"
                          onClick={() => {
                            setSelectedEmployee(emp);
                            setName(emp.name || "");
                            setEmail(emp.email || "");
                            setManagerEmail(emp.manager_email || "");
                            setRole(emp.role || "");
                          }}
                        >
                          <td className="px-3 py-2 font-medium text-slate-900">{emp.name}</td>
                          <td className="px-3 py-2 text-slate-700">{emp.email}</td>
                          <td className="px-3 py-2 text-slate-700">{emp.role}</td>
                          <td className="px-3 py-2">
                            {emp.employment_status === "active" ? (
                              <Pill tone="success">Active</Pill>
                            ) : (
                              <Pill tone="danger">Inactive</Pill>
                            )}
                          </td>
                          <td className="px-3 py-2 text-slate-700">
                            {emp.access_summary ? `${emp.access_summary.granted}/${emp.access_summary.total} granted` : "—"}
                          </td>
                          <td className="px-3 py-2 text-slate-500">
                            {new Date(emp.updated_at).toLocaleDateString()}
                          </td>
                        </tr>
                      ))}

                      {(dashboard?.employees || []).length === 0 && (
                        <tr>
                          <td colSpan={6} className="px-3 py-4 text-center text-slate-500">
                            No employees found.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>

                <div className="flex items-center justify-between">
                  <div className="text-xs text-slate-500">
                    Page {dashboard?.pagination?.page || 1} of {dashboard?.pagination?.total_pages || 1}
                  </div>

                  <div className="flex gap-2">
                    <Button
                      disabled={(dashboard?.pagination?.page || 1) <= 1}
                      onClick={() => setPage((p) => Math.max(1, p - 1))}
                    >
                      Previous
                    </Button>
                    <Button
                      disabled={(dashboard?.pagination?.page || 1) >= (dashboard?.pagination?.total_pages || 1)}
                      onClick={() => setPage((p) => p + 1)}
                    >
                      Next
                    </Button>
                  </div>
                </div>
              </div>
            </Card>

            <Card title="Notifications" subtitle="Slack + Email via MCP">
              <pre className="max-h-[220px] overflow-auto rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs">
                {JSON.stringify(notifications, null, 2)}
              </pre>
              <div className="mt-2 text-[11px] text-slate-500">
                If this is empty, your frontend is likely calling the wrong API base. Set NEXT_PUBLIC_API_BASE to port 9000.
              </div>
            </Card>

            <Card
              title="Audit / Tool Evidence"
              subtitle="Deterministic outcomes (Lifecycle mode)"
              right={access?.audit_id ? <Pill tone="success">{access.audit_id}</Pill> : <Pill>—</Pill>}
            >
              <pre className="max-h-[220px] overflow-auto rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs">
                {JSON.stringify(access || {}, null, 2)}
              </pre>
            </Card>

            <Card title="RAG Sources" subtitle="Where grounding came from">
              <pre className="max-h-[220px] overflow-auto rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs">
                {JSON.stringify(resp?.rag_sources || resp?.rag_sources_detail || {}, null, 2)}
              </pre>
            </Card>
          </div>
        </div>
      </div>
    </main>
  );
}