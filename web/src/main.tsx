import React, { useCallback, useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity,
  ArrowDownToLine,
  ArrowRight,
  BookOpen,
  Check,
  CheckCircle2,
  ChevronRight,
  ChevronLeft,
  Link2,
  Clock3,
  Code2,
  FileText,
  GitBranch,
  Globe2,
  Layers3,
  LayoutDashboard,
  LockKeyhole,
  LogOut,
  Network,
  Plus,
  RefreshCw,
  Search,
  Settings2,
  Shield,
  ShieldCheck,
  Square,
  Terminal,
  Trash2,
  Workflow,
  UsersRound,
  X,
  Zap,
} from "lucide-react";
import "./style.css";
import { api } from "./api";
import { FindingTriage, type TriageFinding } from "./triage";
import { RuntimePanel, PolicySummary, type ExecutionPolicy } from "./runtime";
import { EvidenceGraph } from "./graph";
import {
  CoverageOverview,
  CoverageTable,
  coverageNames,
  type Coverage,
  type CoverageSummary,
} from "./coverage";
import { useRecords, Pagination, AssetPicker, RecordState } from "./records";
import { useNavigation } from "./navigation";
import { FindingRecords } from "./finding-records";
import {
  readNavigation,
  TASK_STATUSES,
  type ListPosition,
  type HistoryMode,
} from "./navigation-state";
import Modal from "./components/Modal";
import { UserPanel, PasswordPanel, roleNames, type User } from "./identity";

type Asset = {
  completed_check_count?: number;
  coverage_summary?: CoverageSummary | null;
  id: string;
  name: string;
  url: string;
  type: string;
  owner: string;
  tags: string[];
  authorization_rules: unknown[];
  revision?: number;
  archived_at?: number | null;
};
type Task = {
  id: string;
  name: string;
  goal: string;
  status: string;
  asset_ids: string[];
  checks: string[];
  workers: number;
  planner: string;
  created_at: number;
  done: number;
  errors: number;
  scope_snapshot: Asset[];
  plan?: string[];
  retest_of?: string;
  retry_of?: string;
  execution_policy?: ExecutionPolicy;
  termination_reason?: string | null;
  queue_wait_ms?: number;
};
type Finding = TriageFinding & {
  id: string;
  title: string;
  severity: string;
  status: string;
  asset_id: string;
  asset_name: string;
  check: string;
  confidence: string;
  remediation: string;
  evidence: unknown;
  task_ids?: string[];
  task_count?: number;
  evidence_reference_count?: number;
  related_ids_omitted?: boolean;
  created_at: number;
};
type Event = {
  seq: number;
  ts: number;
  task_id: string | null;
  level: string;
  message: string;
  detail: Record<string, unknown>;
};
type Tool = {
  id: string;
  name: string;
  description: string;
  category: string;
  risk: string;
};
type Overview = {
  coverage_summary?: CoverageSummary;
  assets: Asset[];
  tasks: Task[];
  findings: Finding[];
  coverage: Coverage[];
  observations: { id: string; asset_id: string; url: string }[];
  events: Event[];
  stats: Record<string, number>;
};
type Observation = {
  id: string;
  url: string;
  asset_id: string;
  task_id: string;
  asset_name?: string | null;
  task_name?: string | null;
  created_at: number;
};
type Settings = {
  version: string;
  lab_mode: boolean;
  llm_configured: boolean;
  llm_model: string;
  request_budget: number;
  max_workers: number;
  execution_policy: ExecutionPolicy;
  agents: { id: string; name: string; role: string; tools: string[] }[];
};
type Schedule = {
  id: string;
  task: { name: string };
  enabled: boolean;
  interval_hours: number;
  next_at: number;
};
type Note = { id: string; title: string; content: string; created_at: number };
type Traffic = {
  id: string;
  task_id: string;
  url: string;
  method: string;
  status: number;
  elapsed_ms: number;
  bytes: number;
  headers: unknown;
  body_sha256: string;
  address: string;
  created_at: number;
};
const initial: Overview = {
  assets: [],
  tasks: [],
  findings: [],
  coverage: [],
  observations: [],
  events: [],
  stats: {},
};
const statusNames: Record<string, string> = {
  pending: "승인 대기",
  queued: "대기 중",
  running: "실행 중",
  stopping: "중지 중",
  stopped: "중지됨",
  completed: "완료",
  failed: "실패",
  interrupted: "중단됨",
  rejected: "승인 거절",
  open: "미조치",
  resolved: "해결됨",
  accepted: "위험 수용",
  reproduced: "여전히 재현됨",
  inconclusive: "판정 불가",
};
const severityNames: Record<string, string> = {
  critical: "Critical",
  high: "High",
  medium: "Medium",
  low: "Low",
  info: "Info",
};
const confidenceNames: Record<string, string> = {
  configuration: "설정 관찰",
  review: "검토 필요",
  "policy-mismatch": "권한 규칙 불일치",
};
const pages = [
  {
    id: "overview",
    name: "대시보드",
    icon: LayoutDashboard,
    group: "WORKSPACE",
  },
  { id: "tasks", name: "검증 작업", icon: Workflow },
  { id: "assets", name: "자산", icon: Globe2 },
  { id: "observations", name: "관찰 링크", icon: Link2 },
  { id: "findings", name: "발견 사항", icon: ShieldCheck },
  { id: "graph", name: "탐색 경로", icon: GitBranch },
  {
    id: "approvals",
    name: "실행 승인",
    icon: LockKeyhole,
    group: "OPERATIONS",
  },
  { id: "traffic", name: "트래픽 기록", icon: Activity },
  { id: "reports", name: "보고서", icon: FileText },
  { id: "schedules", name: "예약 검증", icon: Clock3 },
  { id: "notes", name: "워크스페이스", icon: BookOpen },
  { id: "agents", name: "에이전트 & 도구", icon: Layers3, group: "SYSTEM" },
  { id: "users", name: "사용자 관리", icon: UsersRound },
  { id: "settings", name: "시스템 설정", icon: Settings2 },
];

const date = (ts: number) =>
  new Date(ts * 1000).toLocaleString("ko-KR", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
const Badge = ({ value }: { value: string }) => (
  <span className={"badge " + value}>
    {statusNames[value] || severityNames[value] || value}
  </span>
);
function Empty({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="empty">
      <div className="empty-icon">
        <Network size={28} />
      </div>
      <h3>{title}</h3>
      <p>{description}</p>
      {action}
    </div>
  );
}

function Auth({
  setup,
  onSuccess,
}: {
  setup: boolean;
  onSuccess: (user: User) => void;
}) {
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState(""),
    [token, setToken] = useState(""),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const result = await api<{ user: User }>(
        "/auth/" + (setup ? "setup" : "login"),
        "POST",
        {
          username,
          password,
          setup_token: token,
        },
      );
      onSuccess(result.user);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="auth-page">
      <div className="auth-story">
        <div className="brand">
          <span className="brand-mark">
            <Shield size={25} />
          </span>
          OPEN AEGIS
        </div>
        <div>
          <span className="eyebrow">OPEN SOURCE · SELF HOSTED</span>
          <h1>
            보안을 확인하고.
            <br />
            <em>증거로 연결하세요.</em>
          </h1>
          <p>
            자산 파악부터 검증, 수정 확인까지.
            <br />
            팀이 함께 사용하는 보안 워크스페이스.
          </p>
          <div className="auth-pill">
            <span className="live-dot" /> Your infrastructure. Your evidence.
          </div>
        </div>
        <span className="subtle">
          OPEN AEGIS / SECURITY VALIDATION WORKSPACE
        </span>
      </div>
      <div className="auth-card">
        <div className="section-icon">
          <LockKeyhole size={24} />
        </div>
        <h2>{setup ? "워크스페이스 시작하기" : "다시 만나서 반갑습니다"}</h2>
        <p>
          {setup
            ? "관리자 비밀번호를 설정하고 첫 자산을 연결하세요."
            : "계정으로 로그인하면 역할에 맞는 기능을 사용할 수 있습니다."}
        </p>
        <form onSubmit={submit}>
          <label>
            사용자 이름
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              maxLength={64}
              pattern="[a-zA-Z0-9_.-]+"
              required
            />
          </label>
          <label>
            비밀번호
            <input
              type="password"
              minLength={12}
              maxLength={256}
              required
              autoComplete={setup ? "new-password" : "current-password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="12자 이상 입력하세요"
            />
          </label>
          {setup && (
            <label>
              설치 토큰 <span className="subtle">원격 설치 시 필요</span>
              <input
                type="password"
                value={token}
                onChange={(e) => setToken(e.target.value)}
                autoComplete="off"
                placeholder="로컬 설치에서는 비워두세요"
              />
            </label>
          )}
          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}
          <button className="primary full" disabled={busy}>
            {busy ? "연결 중…" : setup ? "워크스페이스 만들기" : "로그인"}
            <ArrowRight size={16} />
          </button>
        </form>
        <div className="auth-foot">
          <ShieldCheck size={15} /> 비밀번호는 해시로 저장됩니다.
        </div>
      </div>
    </div>
  );
}

function App() {
  const [overviewLoaded, setOverviewLoaded] = useState(false);
  const [auth, setAuth] = useState<{
    setup_required: boolean;
    authenticated: boolean;
    user?: User | null;
  } | null>(null);
  const [overview, setOverview] = useState<Overview>(initial),
    [tools, setTools] = useState<Tool[]>([]),
    [settings, setSettings] = useState<Settings | null>(null);
  const navigation = useNavigation(pages.map((item) => item.id));
  const { page, list } = navigation;
  const search = list.search,
    filter = list.filter,
    showArchived = list.archived;
  const setSearch = (value: string) =>
    navigation.updateList({ search: value }, "replace");
  const setFilter = (value: string) => navigation.updateList({ filter: value });
  const setShowArchived = (value: boolean) =>
    navigation.updateList({ archived: value });
  const [modal, setModal] = useState<
    "asset" | "task" | "import" | "note" | null
  >(null);
  const [editingAsset, setEditingAsset] = useState<Asset | null>(null);
  const [archivingAsset, setArchivingAsset] = useState<Asset | null>(null);
  const [taskAssetId, setTaskAssetId] = useState<string | null>(null);
  const [selectedTask, setSelectedTask] = useState<Task | null>(null),
    [taskDetail, setTaskDetail] = useState<{
      events: Event[];
      coverage: Coverage[];
      findings: Finding[];
    } | null>(null);
  const [selectedFinding, setSelectedFinding] = useState<{
    finding: Finding;
    evidence: unknown[];
    retests: {
      id: string;
      conclusion: string;
      created_at: number;
      state_note?: string;
    }[];
  } | null>(null);
  const [trafficDetail, setTrafficDetail] = useState<Traffic | null>(null);
  const [toast, setToast] = useState(""),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [connection, setConnection] = useState(true);
  const [formError, setFormError] = useState("");
  const actionInFlight = useRef(false);
  const toastTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const refreshSequence = useRef(0);
  const message = (text: string) => {
    setToast(text);
    if (toastTimer.current) clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToast(""), 4000);
  };
  const refresh = useCallback(async () => {
    const sequence = ++refreshSequence.current;
    try {
      const [data, catalog, config, identity] = await Promise.all([
        api<Overview>("/overview"),
        api<Tool[]>("/tools"),
        api<Settings>("/settings"),
        api<{ setup_required: boolean; authenticated: boolean; user?: User }>(
          "/auth/status",
        ),
      ]);
      if (sequence !== refreshSequence.current) return;
      setAuth(identity);
      setOverview(data);
      setOverviewLoaded(true);
      setTools(catalog);
      setSettings(config);
      setConnection(true);
      setError("");
    } catch (e) {
      if (sequence !== refreshSequence.current) return;
      setConnection(false);
      setError((e as Error).message);
    }
  }, []);
  useEffect(() => {
    api<{ setup_required: boolean; authenticated: boolean; user?: User }>(
      "/auth/status",
    )
      .then(setAuth)
      .catch((e) => setError(e.message));
    const expired = () => {
      setAuth({ authenticated: false, setup_required: false });
      setOverviewLoaded(false);
      refreshSequence.current++;
    };
    window.addEventListener("aegis-session-expired", expired);
    return () => window.removeEventListener("aegis-session-expired", expired);
  }, []);
  useEffect(() => {
    if (auth && !auth.authenticated) {
      setOverviewLoaded(false);
      setSelectedTask(null);
      setSelectedFinding(null);
      setTrafficDetail(null);
      setModal(null);
      setArchivingAsset(null);
    }
  }, [auth?.authenticated]);
  useEffect(() => {
    if (!auth?.authenticated) return;
    void refresh();
    const timer = setInterval(() => void refresh(), 4000);
    let cursor = 0,
      source: EventSource | null = null,
      reconnect: ReturnType<typeof setTimeout> | null = null,
      closed = false;
    let eventRefresh: ReturnType<typeof setTimeout> | null = null;
    function connect() {
      if (closed) return;
      source = new EventSource("/api/events/stream?after=" + cursor);
      source.onmessage = (e) => {
        cursor = Math.max(cursor, Number(e.lastEventId));
        if (!eventRefresh)
          eventRefresh = setTimeout(() => {
            eventRefresh = null;
            void refresh();
          }, 250);
      };
      source.onerror = () => {
        source?.close();
        if (!closed) reconnect = setTimeout(connect, 3000);
      };
    }
    connect();
    return () => {
      closed = true;
      clearInterval(timer);
      source?.close();
      if (reconnect) clearTimeout(reconnect);
      if (eventRefresh) clearTimeout(eventRefresh);
    };
  }, [auth?.authenticated, refresh]);
  useEffect(() => {
    if (!selectedTask) return;
    let active = true;
    const load = () =>
      api<{
        task: Task;
        events: Event[];
        coverage: Coverage[];
        findings: Finding[];
      }>("/tasks/" + selectedTask.id)
        .then((d) => {
          if (!active) return;
          setSelectedTask(d.task);
          setTaskDetail(d);
        })
        .catch((e) => setError(e.message));
    void load();
    const timer = setInterval(load, 2500);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [selectedTask?.id]);
  async function act(
    path: string,
    method = "POST",
    body?: unknown,
    success = "적용했습니다.",
  ) {
    if (busy || actionInFlight.current) return;
    actionInFlight.current = true;
    setBusy(true);
    try {
      const result = await api(path, method, body);
      await refresh();
      window.dispatchEvent(new Event("aegis-records-changed"));
      message(success);
      return result;
    } catch (e) {
      setError((e as Error).message);
    } finally {
      actionInFlight.current = false;
      setBusy(false);
    }
  }
  const openModal = (value: typeof modal) => {
    setFormError("");
    setEditingAsset(null);
    setTaskAssetId(null);
    setModal(value);
  };
  const closeModal = useCallback(() => setModal(null), []);
  const closeTask = useCallback(() => {
    setSelectedTask(null);
    setTaskDetail(null);
  }, []);
  const findingRequest = useRef(0);
  const [findingReload, setFindingReload] = useState(0);
  const closeFinding = useCallback(() => {
    findingRequest.current++;
    setSelectedFinding(null);
  }, []);
  const closeTraffic = useCallback(() => setTrafficDetail(null), []);
  const recordKind = auth?.authenticated
    ? (
        {
          assets: "assets",
          tasks: "tasks",
          approvals: "tasks",
          reports: "tasks",
          findings: "findings",
          traffic: "traffic",
          notes: "notes",
          schedules: "schedules",
          observations: "observations",
        } as Record<string, string>
      )[page] || null
    : null;
  const recordFilters: Record<string, string> = {};
  if (page === "assets") recordFilters.archived = String(showArchived);
  if (page === "approvals") recordFilters.status = "pending";
  else if (page === "tasks" && filter !== "all") recordFilters.status = filter;
  if (page === "findings" && filter !== "all") recordFilters.severity = filter;
  if (page === "schedules" && filter !== "all") recordFilters.enabled = filter;
  const navigationKey = JSON.stringify({ page, list });
  const changeRecordPosition = useCallback(
    (position: ListPosition, mode: HistoryMode = "push") => {
      // An old response/event must not rewrite a newly visited route or filter.
      if (
        JSON.stringify(
          readNavigation(
            location.search,
            pages.map((item) => item.id),
          ),
        ) !== navigationKey
      )
        return;
      navigation.updateList(position, mode);
    },
    [navigationKey, navigation.updateList],
  );
  const records = useRecords<
    Asset | Task | Finding | Traffic | Note | Schedule | Observation
  >(recordKind, search, recordFilters, {
    ...list,
    onPositionChange: changeRecordPosition,
  });
  const visibleTasks = recordKind === "tasks" ? (records.items as Task[]) : [];
  const visibleFindings =
    page === "findings" ? (records.items as Finding[]) : [];
  const visibleAssets = page === "assets" ? (records.items as Asset[]) : [];
  const traffic = page === "traffic" ? (records.items as Traffic[]) : [];
  const notes = page === "notes" ? (records.items as Note[]) : [];
  const observations =
    page === "observations" ? (records.items as Observation[]) : [];
  const schedules = page === "schedules" ? (records.items as Schedule[]) : [];
  const pending =
    page === "approvals"
      ? visibleTasks
      : overview.tasks.filter((t) => t.status === "pending");
  const navigate = (value: string, fresh = false) => {
    navigation.navigate(value, fresh);
    setError("");
  };
  useEffect(() => {
    findingRequest.current++;
    setSelectedTask(null);
    setTaskDetail(null);
    setSelectedFinding(null);
    setTrafficDetail(null);
    setModal(null);
    setArchivingAsset(null);
  }, [page]);
  useEffect(() => {
    const close = () => {
      findingRequest.current++;
      setSelectedTask(null);
      setTaskDetail(null);
      setSelectedFinding(null);
      setTrafficDetail(null);
      setModal(null);
      setArchivingAsset(null);
    };
    window.addEventListener("popstate", close);
    return () => window.removeEventListener("popstate", close);
  }, []);
  async function openFinding(id: string, reload = false) {
    const request = ++findingRequest.current;
    try {
      const result = await api<NonNullable<typeof selectedFinding>>(
        "/findings/" + id,
      );
      if (request === findingRequest.current) {
        setSelectedFinding(result);
        if (reload) setFindingReload((v) => v + 1);
      }
    } catch (e) {
      if (request === findingRequest.current) setError((e as Error).message);
    }
  }
  async function submitForm(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (busy) return;
    setBusy(true);
    setFormError("");
    const data = new FormData(e.currentTarget);
    try {
      if (modal === "asset") {
        const rules = String(data.get("rules") || "").trim();
        await api(
          editingAsset ? "/assets/" + editingAsset.id : "/assets",
          editingAsset ? "PUT" : "POST",
          {
            name: data.get("name"),
            url: data.get("url"),
            type: data.get("type"),
            owner: data.get("owner"),
            tags: String(data.get("tags") || "")
              .split(",")
              .map((t) => t.trim())
              .filter(Boolean),
            authorization_rules: rules ? JSON.parse(rules) : [],
            authorized: data.get("authorized") === "on",
          },
        );
        message(
          editingAsset
            ? "자산을 수정했습니다. 기존 승인 대기 계획은 다시 만들어야 합니다."
            : "자산을 등록했습니다.",
        );
      } else if (modal === "import") {
        await api(
          "/assets/import",
          "POST",
          JSON.parse(String(data.get("json"))),
        );
        message("자산을 가져왔습니다.");
      } else if (modal === "task") {
        const body = {
          name: data.get("name"),
          goal: data.get("goal"),
          asset_ids: data.getAll("asset"),
          checks: data.getAll("check"),
          workers: Number(data.get("workers")),
          planner: data.get("planner"),
        };
        const interval = Number(data.get("interval"));
        await api(
          interval ? "/schedules" : "/tasks",
          "POST",
          interval ? { ...body, interval_hours: interval } : body,
        );
        navigate(interval ? "schedules" : "approvals", true);
        message(
          interval
            ? "예약을 만들었습니다. 생성된 작업은 승인이 필요합니다."
            : "계획을 만들었습니다. 실행 범위를 확인하고 승인하세요.",
        );
      } else if (modal === "note") {
        await api("/notes", "POST", {
          title: data.get("title"),
          content: data.get("content"),
        });
        navigate("notes", true);
        message("노트를 저장했습니다.");
      }
      await refresh();
      window.dispatchEvent(new Event("aegis-records-changed"));
      setModal(null);
    } catch (e) {
      setFormError(
        e instanceof SyntaxError
          ? "JSON 형식을 확인하세요."
          : (e as Error).message,
      );
    } finally {
      setBusy(false);
    }
  }
  if (!auth || (auth.authenticated && !overviewLoaded))
    return (
      <div className="loading">
        <Shield size={32} />
        <p>{error || "워크스페이스에 연결하고 있습니다…"}</p>
        {error && (
          <button
            onClick={() => {
              if (auth?.authenticated) void refresh();
              else
                void api<{ setup_required: boolean; authenticated: boolean }>(
                  "/auth/status",
                )
                  .then(setAuth)
                  .catch((e) => setError(e.message));
            }}
          >
            다시 연결
          </button>
        )}
      </div>
    );
  if (!auth.authenticated)
    return (
      <Auth
        setup={auth.setup_required}
        onSuccess={(user) =>
          setAuth({ setup_required: false, authenticated: true, user })
        }
      />
    );
  const canOperate =
    auth.user?.role === "admin" || auth.user?.role === "operator";
  const canApprove = auth.user?.role === "admin";
  const title = pages.find((p) => p.id === page)?.name;
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a
          className="brand"
          href="#"
          onClick={(e) => {
            e.preventDefault();
            navigate("overview");
          }}
        >
          <span className="brand-mark">
            <Shield size={23} />
          </span>
          <span>
            OPEN AEGIS<small>SECURITY WORKSPACE</small>
          </span>
        </a>
        <div className="workspace-switch">
          <span className="workspace-avatar">W</span>
          <div>
            내 워크스페이스<small>Self-hosted · Local</small>
          </div>
          <ChevronRight size={14} />
        </div>
        <nav>
          {pages
            .filter((p) => p.id !== "users" || canApprove)
            .map((p) => (
              <React.Fragment key={p.id}>
                {p.group && <div className="nav-label">{p.group}</div>}
                <button
                  aria-label={p.name}
                  className={"nav-item " + (page === p.id ? "active" : "")}
                  onClick={() => navigate(p.id)}
                >
                  <p.icon size={18} />
                  <span>{p.name}</span>
                  {p.id === "approvals" && pending.length > 0 && (
                    <b>{pending.length}</b>
                  )}
                  {p.id === "findings" && overview.stats.findings > 0 && (
                    <small>{overview.stats.findings}</small>
                  )}
                </button>
              </React.Fragment>
            ))}
        </nav>
        <div className="sidebar-bottom">
          <span className="open-source">
            <Code2 size={14} /> OPEN SOURCE{" "}
            <span>v{settings?.version || "0.1.0"}</span>
          </span>
          <button
            className="nav-item"
            onClick={async () => {
              await act("/auth/logout");
              setAuth({ setup_required: false, authenticated: false });
            }}
          >
            <LogOut size={17} />
            로그아웃
          </button>
        </div>
      </aside>
      <main className="main">
        <header className="topbar">
          <div>
            <nav className="navigation-controls" aria-label="탐색 이력">
              <button
                aria-label="이전 탐색"
                title="이전 탐색"
                disabled={!navigation.canBack}
                onClick={navigation.back}
              >
                <ChevronLeft size={18} />
              </button>
              <button
                aria-label="다음 탐색"
                title="다음 탐색"
                disabled={!navigation.canForward}
                onClick={navigation.forward}
              >
                <ChevronRight size={18} />
              </button>
            </nav>
            <div className="navigation-crumb">
              <span>워크스페이스</span>
              <ChevronRight size={13} />
              <strong>{title}</strong>
            </div>
          </div>
          <div className="topbar-right">
            <span className="connection">
              <span className={connection ? "live-dot" : "offline-dot"} />
              {connection ? "시스템 연결됨" : "연결 확인 필요"}
            </span>
            <span className="role-identity">
              {auth.user?.name || "사용자"} ·{" "}
              {roleNames[auth.user?.role || "viewer"]}
            </span>
            <span className="topbar-avatar">
              {(auth.user?.username || "U").slice(0, 2).toUpperCase()}
            </span>
          </div>
        </header>
        <div className="content">
          {error && (!recordKind || error !== records.error) && (
            <div className="error-banner" role="alert">
              <span>{error}</span>
              <button aria-label="오류 닫기" onClick={() => setError("")}>
                <X size={16} />
              </button>
            </div>
          )}
          <div className="page-head">
            <div>
              <div className="eyebrow">
                {page === "overview"
                  ? "SECURITY POSTURE"
                  : page === "graph"
                    ? "EXPLORATION GRAPH"
                    : "YOUR SECURITY WORKSPACE"}
              </div>
              <h1>{page === "overview" ? "보안 현황을 한눈에." : title}</h1>
              <p>
                {
                  (
                    {
                      overview:
                        "자산의 상태를 확인하고, 근거 있는 검증을 시작하세요.",
                      tasks: "목표를 정하고 실행부터 수정 확인까지 추적하세요.",
                      assets: "검증할 자산과 접근 범위를 한곳에서 관리하세요.",
                      observations:
                        "승인된 검증에서 관찰한 링크와 기록의 출처를 확인하세요.",
                      findings:
                        "실제 관찰한 증거를 바탕으로 조치 우선순위를 정하세요.",
                      graph:
                        "등록된 자산과 수행한 검증, 발견 사항의 연결을 확인하세요.",
                      approvals:
                        "요청 대상과 도구를 확인한 뒤 검증 실행을 승인하세요.",
                      traffic:
                        "검증 중 발생한 HTTP 요청과 응답 메타데이터를 확인하세요.",
                      reports:
                        "검증 범위와 결과, 증거를 공유할 수 있는 형태로 내보내세요.",
                      schedules:
                        "반복 검증을 예약하고 새 작업의 실행 범위를 확인하세요.",
                      notes: "운영 지식과 검증 메모를 팀의 기록으로 남기세요.",
                      agents:
                        "계획·실행·재검증 에이전트와 등록된 검증 도구입니다.",
                      users:
                        "계정과 역할을 관리하세요. 권한 변경은 기존 세션을 만료시킵니다.",
                      settings:
                        "워크스페이스의 실행 정책과 연결 상태를 확인하세요.",
                    } as Record<string, string>
                  )[page]
                }
              </p>
            </div>
            <div className="head-actions">
              {page === "assets" ? (
                <>
                  <button
                    disabled={!canOperate}
                    onClick={() => openModal("import")}
                  >
                    <ArrowDownToLine size={15} />
                    JSON 가져오기
                  </button>
                  <button
                    className="primary"
                    disabled={!canOperate}
                    onClick={() => openModal("asset")}
                  >
                    <Plus size={16} />
                    자산 등록
                  </button>
                </>
              ) : page === "notes" ? (
                <button
                  className="primary"
                  disabled={!canOperate}
                  onClick={() => openModal("note")}
                >
                  <Plus size={16} />
                  노트 작성
                </button>
              ) : ["overview", "tasks", "schedules"].includes(page) ? (
                <button
                  className="primary"
                  disabled={!overview.assets.length || !canOperate}
                  onClick={() => openModal("task")}
                >
                  <Plus size={16} />
                  {page === "schedules" ? "예약 만들기" : "새 검증 작업"}
                </button>
              ) : (
                <button onClick={() => void refresh()}>
                  <RefreshCw size={15} />
                  새로고침
                </button>
              )}
            </div>
          </div>

          {page === "overview" && (
            <>
              <div className="hero-panel">
                <div>
                  <div className="hero-label">
                    <span className="live-dot" /> EVIDENCE FIRST, ALWAYS.
                  </div>
                  <h2>
                    확인할 수 있는 보안.
                    <br />
                    <span>지속할 수 있는 검증.</span>
                  </h2>
                  <p>
                    승인된 자산을 검증하고, 관찰한 결과를 증거로 남깁니다.
                    <br />
                    발견에서 끝나지 않고 수정 확인까지 이어가세요.
                  </p>
                  <button
                    disabled={!canOperate}
                    onClick={() =>
                      overview.assets.length
                        ? openModal("task")
                        : openModal("asset")
                    }
                  >
                    {overview.assets.length
                      ? "검증 계획 만들기"
                      : "첫 자산 연결하기"}
                    <ArrowRight size={16} />
                  </button>
                </div>
                <div className="hero-art" aria-hidden="true">
                  <div className="orbit orbit-one" />
                  <div className="orbit orbit-two" />
                  <div className="orbit orbit-three" />
                  <div className="hero-shield">
                    <ShieldCheck size={66} strokeWidth={1.2} />
                  </div>
                  <span className="orbit-node n1">
                    <Globe2 size={17} />
                  </span>
                  <span className="orbit-node n2">
                    <Check size={17} />
                  </span>
                  <span className="orbit-node n3">
                    <LockKeyhole size={17} />
                  </span>
                  <span className="orbit-note">SCOPE → VALIDATE → VERIFY</span>
                </div>
              </div>
              <div className="stats-grid">
                {[
                  {
                    label: "등록된 자산",
                    value: overview.stats.assets || 0,
                    icon: Globe2,
                    note: "검증 범위에 등록된 대상",
                    color: "cyan",
                  },
                  {
                    label: "미조치 발견 사항",
                    value: overview.stats.findings || 0,
                    icon: ShieldCheck,
                    note: "설정 관찰과 권한 규칙 불일치",
                    color: "orange",
                  },
                  {
                    label: "실행 중인 작업",
                    value: overview.stats.running || 0,
                    icon: Zap,
                    note: `${overview.stats.pending || 0}개 작업이 승인 대기 중`,
                    color: "purple",
                  },
                  {
                    label: "도구별 검증 커버리지",
                    value: overview.coverage_summary?.expected
                      ? `${overview.coverage_summary.percent}%`
                      : "—",
                    icon: Network,
                    note: `${overview.coverage_summary?.completed || 0} / ${overview.coverage_summary?.expected || 0}개 검증 완료 · 최신 승인·현재 범위`,
                    color: "green",
                  },
                ].map((s) => (
                  <div className="stat-card" key={s.label}>
                    <div className="stat-top">
                      {s.label}
                      <span className={"stat-icon " + s.color}>
                        <s.icon size={18} />
                      </span>
                    </div>
                    <strong>{s.value}</strong>
                    <small>{s.note}</small>
                  </div>
                ))}
              </div>
              <div className="dashboard-grid">
                <section className="panel">
                  <div className="panel-head">
                    <h3>
                      최근 검증 작업{" "}
                      <span>
                        {overview.tasks.length} / 전체 {overview.stats.tasks}
                      </span>
                    </h3>
                    <button
                      className="text-button"
                      onClick={() => navigate("tasks")}
                    >
                      전체 보기
                      <ArrowRight size={14} />
                    </button>
                  </div>
                  {overview.tasks.length ? (
                    <div className="task-list">
                      {overview.tasks.slice(0, 4).map((t) => (
                        <button
                          className="task-row"
                          key={t.id}
                          onClick={() => setSelectedTask(t)}
                        >
                          <span className="row-icon">
                            <Workflow size={18} />
                          </span>
                          <div>
                            <strong>{t.name}</strong>
                            <small>
                              {t.asset_ids.length}개 자산 · {t.checks.length}개
                              도구 · {date(t.created_at)}
                            </small>
                          </div>
                          <Badge value={t.status} />
                          <ChevronRight size={15} />
                        </button>
                      ))}
                    </div>
                  ) : (
                    <Empty
                      title="첫 검증을 시작하세요"
                      description="자산을 등록하면 검증 계획을 만들 수 있습니다."
                      action={
                        <button
                          disabled={!canOperate}
                          onClick={() => openModal("asset")}
                        >
                          <Plus size={15} />
                          자산 등록
                        </button>
                      }
                    />
                  )}
                </section>
                <section className="panel">
                  <div className="panel-head">
                    <h3>발견 사항 분포</h3>
                    <span className="subtle">미조치 기준</span>
                  </div>
                  <div className="severity-chart">
                    <div
                      className="donut"
                      style={{
                        background: `conic-gradient(var(--montage-status-negative) 0deg ${(((overview.stats.findings_high || 0) + (overview.stats.findings_critical || 0)) / Math.max(1, overview.stats.findings || 0)) * 360}deg, var(--montage-status-cautionary) 0deg ${(((overview.stats.findings_high || 0) + (overview.stats.findings_critical || 0) + (overview.stats.findings_medium || 0)) / Math.max(1, overview.stats.findings || 0)) * 360}deg, var(--montage-status-positive) 0deg ${(((overview.stats.findings_high || 0) + (overview.stats.findings_critical || 0) + (overview.stats.findings_medium || 0) + (overview.stats.findings_low || 0)) / Math.max(1, overview.stats.findings || 0)) * 360}deg, var(--montage-primary-normal) 0deg 360deg)`,
                      }}
                    >
                      <div>
                        <strong>{overview.stats.findings || 0}</strong>
                        <small>OPEN FINDINGS</small>
                      </div>
                    </div>
                    <div className="legend">
                      {["critical", "high", "medium", "low", "info"].map(
                        (s) => (
                          <div key={s}>
                            <span className={"severity-dot " + s} />
                            <span>{severityNames[s]}</span>
                            <b>{overview.stats[`findings_${s}`] || 0}</b>
                          </div>
                        ),
                      )}
                    </div>
                  </div>
                </section>
              </div>
              <CoverageOverview summary={overview.coverage_summary} />
              <section className="panel activity-panel">
                <div className="panel-head">
                  <h3>워크스페이스 활동</h3>
                  <span className="connection">
                    <span className="live-dot" />
                    실시간
                  </span>
                </div>
                {overview.events.length ? (
                  <div className="event-feed">
                    {overview.events
                      .slice(-5)
                      .reverse()
                      .map((e) => (
                        <div className="event-line" key={e.seq}>
                          <span className={"event-dot " + e.level} />
                          <span>{e.message}</span>
                          <small>{date(e.ts)}</small>
                        </div>
                      ))}
                  </div>
                ) : (
                  <div className="quiet-state">
                    아직 활동이 없습니다. 자산 등록부터 시작하세요.
                  </div>
                )}
              </section>
            </>
          )}

          {recordKind && <Pagination records={records} />}

          {page === "assets" && (
            <>
              <Toolbar
                search={search}
                setSearch={setSearch}
                placeholder="이름, 주소, 소유자로 검색"
                count={records.total}
                error={records.error}
                loading={!records.ready && records.loading}
              >
                <button
                  onClick={() => setShowArchived(!showArchived)}
                  aria-pressed={showArchived}
                >
                  {showArchived ? "활성 자산 보기" : "보관함 보기"}
                </button>
              </Toolbar>
              {!records.ready ? (
                <RecordState records={records} />
              ) : visibleAssets.length ? (
                <div className="asset-grid">
                  {visibleAssets.map((a) => (
                    <section className="panel asset-card" key={a.id}>
                      <div className="asset-card-top">
                        <span className="asset-icon">
                          <Globe2 size={23} />
                        </span>
                        <Badge value={a.archived_at ? "보관됨" : a.type} />
                      </div>
                      <h3>{a.name}</h3>
                      <code>{a.url}</code>
                      <div className="asset-meta">
                        <span>담당자</span>
                        <strong>{a.owner || "미지정"}</strong>
                      </div>
                      <div className="asset-meta">
                        <span>
                          {a.archived_at
                            ? "과거 완료 검증 종류"
                            : "현재 범위 완료 검증"}
                        </span>
                        <strong>
                          {a.archived_at
                            ? a.completed_check_count || 0
                            : a.coverage_summary?.completed || 0}{" "}
                          / {tools.length}
                        </strong>
                      </div>
                      {a.coverage_summary && (
                        <div className="tags" aria-label="검증 상태">
                          {Object.entries(a.coverage_summary.counts)
                            .filter(
                              ([status, count]) =>
                                status !== "completed" && count > 0,
                            )
                            .map(([status, count]) => (
                              <span key={status}>
                                {coverageNames[status]} {count}
                              </span>
                            ))}
                        </div>
                      )}
                      <div className="tags">
                        {a.tags.map((t) => (
                          <span key={t}>{t}</span>
                        ))}
                      </div>
                      <div className="card-foot">
                        <span>
                          <ShieldCheck size={14} />
                          {a.archived_at ? "이력 보존됨" : "범위 등록됨"}
                        </span>
                        {!a.archived_at && (
                          <button
                            className="text-button"
                            disabled={!canOperate}
                            onClick={() => {
                              navigate("tasks");
                              openModal("task");
                              setTaskAssetId(a.id);
                            }}
                          >
                            검증 만들기
                            <ArrowRight size={14} />
                          </button>
                        )}
                      </div>
                      <div className="asset-actions">
                        {!a.archived_at && (
                          <button
                            disabled={!canOperate}
                            onClick={() => {
                              openModal("asset");
                              setEditingAsset(a);
                            }}
                          >
                            수정
                          </button>
                        )}
                        <button
                          disabled={!canOperate}
                          onClick={() => setArchivingAsset(a)}
                        >
                          {a.archived_at ? "복원" : "보관"}
                        </button>
                      </div>
                    </section>
                  ))}
                </div>
              ) : (
                <section className="panel">
                  <Empty
                    title={
                      search
                        ? "검색 결과가 없습니다"
                        : showArchived
                          ? "보관된 자산이 없습니다"
                          : overview.stats.assets
                            ? "표시할 자산이 없습니다"
                            : "아직 등록된 자산이 없습니다"
                    }
                    description="검증 권한이 있는 웹사이트 또는 API 주소를 연결하세요."
                    action={
                      <button
                        className="primary"
                        disabled={!canOperate}
                        onClick={() => openModal("asset")}
                      >
                        <Plus size={16} />
                        {overview.stats.assets ? "자산 등록" : "첫 자산 등록"}
                      </button>
                    }
                  />
                </section>
              )}
              <section className="panel observed-panel">
                <div className="panel-head">
                  <h3>
                    관찰된 엔드포인트{" "}
                    <span>{overview.stats.observations || 0}</span>
                  </h3>
                  <button onClick={() => navigate("observations", true)}>
                    전체 관찰 링크
                  </button>
                </div>
                {overview.observations.length ? (
                  <>
                    <p className="subtle">
                      워크스페이스 전체 · 최근{" "}
                      {Math.min(30, overview.observations.length)}개 · 링크 관찰
                      · 자동 요청 없음
                    </p>
                    {overview.observations.slice(0, 30).map((o) => (
                      <div className="observation" key={o.id}>
                        <GitBranch size={14} />
                        <code>{o.url}</code>
                        <span className="subtle">추가 등록 필요</span>
                      </div>
                    ))}
                  </>
                ) : (
                  <div className="quiet-state">
                    엔드포인트 관찰 도구를 실행하면 범위 내 링크가 표시됩니다.
                  </div>
                )}
              </section>
            </>
          )}

          {page === "observations" && (
            <>
              <Toolbar
                search={search}
                setSearch={setSearch}
                placeholder="링크·자산·작업으로 검색"
                count={records.total}
                error={records.error}
                loading={!records.ready && records.loading}
              />
              <div className="info-strip">
                <Link2 size={18} />
                <span>
                  HTML에서 관찰한 범위 내 링크입니다. 관찰은 접근 가능 여부나
                  취약점 검증 결과가 아닙니다. 이 화면은 링크에 요청하지
                  않습니다.
                </span>
              </div>
              <section className="panel">
                {!records.ready ? (
                  <RecordState records={records} />
                ) : observations.length ? (
                  <div className="table-scroll">
                    <table>
                      <thead>
                        <tr>
                          <th>관찰 링크</th>
                          <th>자산</th>
                          <th>최근 관찰 작업</th>
                          <th>관찰 시각</th>
                        </tr>
                      </thead>
                      <tbody>
                        {observations.map((observation) => (
                          <tr key={observation.id}>
                            <td>
                              <code className="observation-url">
                                {observation.url}
                              </code>
                            </td>
                            <td className="observation-source">
                              {observation.asset_name || "자산 기록 없음"}
                              <small>{observation.asset_id}</small>
                            </td>
                            <td className="observation-source">
                              {observation.task_name || "작업 기록 없음"}
                              <small>{observation.task_id}</small>
                            </td>
                            <td>{date(observation.created_at)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <Empty
                    title={
                      search ? "검색 결과가 없습니다" : "관찰된 링크가 없습니다"
                    }
                    description="엔드포인트 관찰 도구를 승인해 실행하면 범위 내 링크를 기록합니다."
                  />
                )}
              </section>
            </>
          )}

          {page === "tasks" && (
            <>
              <Toolbar
                search={search}
                setSearch={setSearch}
                placeholder="작업 이름으로 검색"
                count={records.total}
                error={records.error}
                loading={!records.ready && records.loading}
              >
                <select
                  aria-label="작업 상태"
                  value={filter}
                  onChange={(e) => setFilter(e.target.value)}
                >
                  <option value="all">모든 상태</option>
                  {TASK_STATUSES.map((s) => (
                    <option key={s} value={s}>
                      {statusNames[s]}
                    </option>
                  ))}
                </select>
              </Toolbar>
              <section className="panel">
                {!records.ready ? (
                  <RecordState records={records} />
                ) : visibleTasks.length ? (
                  <div className="table-scroll">
                    <table>
                      <thead>
                        <tr>
                          <th>검증 작업</th>
                          <th>상태</th>
                          <th>범위</th>
                          <th>진행률</th>
                          <th>생성 시각</th>
                          <th />
                        </tr>
                      </thead>
                      <tbody>
                        {visibleTasks.map((t) => (
                          <tr key={t.id}>
                            <td>
                              <button
                                className="table-link"
                                onClick={() => setSelectedTask(t)}
                              >
                                <Workflow size={17} />
                                <div>
                                  {t.name}
                                  <small>
                                    {t.planner === "ai"
                                      ? "AI Planner"
                                      : "Rule-based Planner"}{" "}
                                    · {t.workers} workers
                                  </small>
                                </div>
                              </button>
                            </td>
                            <td>
                              <Badge value={t.status} />
                            </td>
                            <td>{t.asset_ids.length}개 자산</td>
                            <td>
                              <div className="progress-cell">
                                <div className="progress">
                                  <span
                                    style={{
                                      width:
                                        Math.round(
                                          (t.done / t.asset_ids.length) * 100,
                                        ) + "%",
                                    }}
                                  />
                                </div>
                                <small>
                                  {t.done}/{t.asset_ids.length}
                                </small>
                              </div>
                            </td>
                            <td className="subtle">{date(t.created_at)}</td>
                            <td>
                              <button
                                className="icon-button"
                                onClick={() => setSelectedTask(t)}
                                aria-label={t.name + " 상세"}
                              >
                                <ChevronRight size={17} />
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <Empty
                    title={
                      search || filter !== "all" || overview.stats.tasks
                        ? "일치하는 작업이 없습니다"
                        : "아직 검증 작업이 없습니다"
                    }
                    description="등록한 자산을 선택해 첫 검증 계획을 만드세요."
                  />
                )}
              </section>
            </>
          )}

          {page === "findings" && (
            <>
              <Toolbar
                search={search}
                setSearch={setSearch}
                placeholder="발견 사항 또는 자산으로 검색"
                count={records.total}
                error={records.error}
                loading={!records.ready && records.loading}
              >
                <select
                  aria-label="심각도"
                  value={filter}
                  onChange={(e) => setFilter(e.target.value)}
                >
                  <option value="all">모든 심각도</option>
                  {Object.keys(severityNames).map((s) => (
                    <option key={s} value={s}>
                      {severityNames[s]}
                    </option>
                  ))}
                </select>
              </Toolbar>
              <section className="panel">
                {!records.ready ? (
                  <RecordState records={records} />
                ) : visibleFindings.length ? (
                  <div className="table-scroll">
                    <table>
                      <thead>
                        <tr>
                          <th>발견 사항</th>
                          <th>심각도</th>
                          <th>자산</th>
                          <th>판정 유형</th>
                          <th>상태</th>
                          <th />
                        </tr>
                      </thead>
                      <tbody>
                        {visibleFindings.map((f) => (
                          <tr key={f.id}>
                            <td>
                              <button
                                className="table-link"
                                onClick={() => void openFinding(f.id)}
                              >
                                <ShieldCheck size={17} />
                                <div>
                                  {f.title}
                                  <small>
                                    {tools.find((t) => t.id === f.check)
                                      ?.name || f.check}
                                  </small>
                                </div>
                              </button>
                            </td>
                            <td>
                              <Badge value={f.severity} />
                            </td>
                            <td>{f.asset_name}</td>
                            <td className="subtle">
                              {confidenceNames[f.confidence]}
                            </td>
                            <td>
                              <Badge value={f.status} />
                            </td>
                            <td>
                              <button
                                className="icon-button"
                                onClick={() => void openFinding(f.id)}
                                aria-label={f.title + " 상세"}
                              >
                                <ChevronRight size={17} />
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <Empty
                    title="표시할 발견 사항이 없습니다"
                    description="발견 사항이 없다는 사실만으로 전체 시스템의 안전을 보증하지는 않습니다."
                  />
                )}
              </section>
            </>
          )}

          {page === "approvals" && (
            <>
              <Toolbar
                search={search}
                setSearch={setSearch}
                placeholder="승인할 작업으로 검색"
                count={records.total}
                error={records.error}
                loading={!records.ready && records.loading}
              />
              <div className="info-strip">
                <LockKeyhole size={18} />
                <span>
                  승인하면 표시된 자산과 도구에 한해 HTTP GET 검증이 실행됩니다.
                  범위 밖 주소로는 이동하지 않습니다.
                </span>
              </div>
              {!records.ready ? (
                <RecordState records={records} />
              ) : pending.length ? (
                <div className="approval-grid">
                  {pending.map((t) => (
                    <section className="panel approval-card" key={t.id}>
                      <div className="approval-heading">
                        <span className="section-icon">
                          <LockKeyhole size={19} />
                        </span>
                        <Badge value="pending" />
                      </div>
                      <h3>{t.name}</h3>
                      <p>{t.goal}</p>
                      <div className="approval-scope">
                        <h4>요청 범위</h4>
                        {t.scope_snapshot.map((a) => (
                          <div key={a.id}>
                            <Globe2 size={14} />
                            <code>{a.url}</code>
                          </div>
                        ))}
                      </div>
                      <div className="tags">
                        {t.checks.map((c) => (
                          <span key={c}>
                            {tools.find((t) => t.id === c)?.name || c}
                          </span>
                        ))}
                      </div>
                      <div className="approval-budget">
                        {t.workers} workers · 자산별 최대{" "}
                        {t.execution_policy?.request_budget ||
                          settings?.request_budget}{" "}
                        요청 · GET only
                      </div>
                      {t.execution_policy && (
                        <PolicySummary policy={t.execution_policy} />
                      )}
                      <div className="approval-buttons">
                        <button
                          disabled={busy || !canOperate}
                          onClick={() =>
                            void act(
                              "/tasks/" + t.id + "/stop",
                              "POST",
                              undefined,
                              "승인을 거절했습니다.",
                            )
                          }
                        >
                          <X size={15} />
                          거절
                        </button>
                        <button
                          className="primary"
                          disabled={busy || !canApprove}
                          onClick={() =>
                            void act(
                              "/tasks/" + t.id + "/approve",
                              "POST",
                              undefined,
                              "승인했습니다. 검증을 시작합니다.",
                            )
                          }
                        >
                          <Check size={16} />
                          승인하고 실행
                        </button>
                      </div>
                    </section>
                  ))}
                </div>
              ) : (
                <section className="panel">
                  <Empty
                    title="표시할 승인 요청이 없습니다"
                    description="새 검증 작업과 재검증은 이곳에서 범위를 확인하고 승인합니다."
                  />
                </section>
              )}
            </>
          )}

          {page === "graph" && (
            <EvidenceGraph
              tools={tools}
              onFinding={(id) => void openFinding(id)}
            />
          )}

          {page === "traffic" && (
            <>
              <Toolbar
                search={search}
                setSearch={setSearch}
                placeholder="요청 URL로 검색"
                count={records.total}
                error={records.error}
                loading={!records.ready && records.loading}
              />
              <section className="panel">
                {!records.ready ? (
                  <RecordState records={records} />
                ) : traffic.length ? (
                  <div className="table-scroll">
                    <table>
                      <thead>
                        <tr>
                          <th>요청</th>
                          <th>응답</th>
                          <th>소요 시간</th>
                          <th>수신 크기</th>
                          <th>시각</th>
                          <th />
                        </tr>
                      </thead>
                      <tbody>
                        {traffic.map((t) => (
                          <tr key={t.id}>
                            <td>
                              <button
                                className="table-link mono"
                                onClick={() => setTrafficDetail(t)}
                              >
                                <span className="method">{t.method}</span>
                                {t.url}
                              </button>
                            </td>
                            <td>
                              <Badge value={String(t.status)} />
                            </td>
                            <td>{t.elapsed_ms} ms</td>
                            <td>{t.bytes.toLocaleString()} B</td>
                            <td className="subtle">{date(t.created_at)}</td>
                            <td>
                              <button
                                className="icon-button"
                                onClick={() => setTrafficDetail(t)}
                                aria-label="트래픽 상세"
                              >
                                <ChevronRight size={17} />
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <Empty
                    title="표시할 HTTP 요청이 없습니다"
                    description="검증을 실행하면 응답 메타데이터와 본문 해시가 저장됩니다."
                  />
                )}
              </section>
              <p className="footnote">
                인증 헤더·쿠키 값·응답 본문·쿼리 값은 저장하지 않습니다. 이
                기록은 검증 요청에 한정되며 전체 네트워크 패킷 캡처가 아닙니다.
              </p>
            </>
          )}

          {page === "reports" && (
            <>
              <Toolbar
                search={search}
                setSearch={setSearch}
                placeholder="보고서를 내보낼 작업으로 검색"
                count={records.total}
                error={records.error}
                loading={!records.ready && records.loading}
              />
              <div className="report-options">
                {[
                  {
                    format: "markdown",
                    label: "Markdown 보고서",
                    desc: "검증 범위, 발견 사항, 수정 가이드를 공유하세요.",
                    icon: FileText,
                  },
                  {
                    format: "json",
                    label: "JSON 증거 묶음",
                    desc: "작업·증거·트래픽·커버리지 원본 기록을 내보냅니다.",
                    icon: Code2,
                  },
                  {
                    format: "csv",
                    label: "CSV 발견 사항",
                    desc: "스프레드시트에서 상태와 우선순위를 관리하세요.",
                    icon: Layers3,
                  },
                ].map((r) => (
                  <section className="panel report-card" key={r.format}>
                    <span className="section-icon">
                      <r.icon size={24} />
                    </span>
                    <h3>{r.label}</h3>
                    <p>{r.desc}</p>
                    <a
                      className="button"
                      href={"/api/reports/export?format=" + r.format}
                      download
                    >
                      <ArrowDownToLine size={15} />
                      전체 내보내기
                    </a>
                  </section>
                ))}
              </div>
              <section className="panel">
                <div className="panel-head">
                  <h3>작업별 보고서</h3>
                </div>
                {!records.ready ? (
                  <RecordState records={records} />
                ) : visibleTasks.length ? (
                  visibleTasks.map((t) => (
                    <div className="report-row" key={t.id}>
                      <span className="row-icon">
                        <FileText size={18} />
                      </span>
                      <div>
                        <strong>{t.name}</strong>
                        <small>
                          {date(t.created_at)} · {statusNames[t.status]}
                        </small>
                      </div>
                      <a
                        className="button"
                        href={
                          "/api/reports/export?format=markdown&task_id=" + t.id
                        }
                        download
                      >
                        <ArrowDownToLine size={14} />
                        보고서
                      </a>
                    </div>
                  ))
                ) : (
                  <div className="quiet-state">
                    {overview.stats.tasks
                      ? "현재 조건에 맞는 작업이 없습니다."
                      : "검증 작업을 만들면 작업별 보고서를 내보낼 수 있습니다."}
                  </div>
                )}
              </section>
            </>
          )}

          {page === "schedules" && (
            <>
              <Toolbar
                search={search}
                setSearch={setSearch}
                placeholder="예약 이름 또는 목표로 검색"
                count={records.total}
                error={records.error}
                loading={!records.ready && records.loading}
              >
                <select
                  aria-label="예약 상태"
                  value={filter}
                  onChange={(e) => setFilter(e.target.value)}
                >
                  <option value="all">모든 예약</option>
                  <option value="true">활성</option>
                  <option value="false">일시 중지</option>
                </select>
              </Toolbar>
              <div className="info-strip">
                <Clock3 size={18} />
                <span>
                  예약 시간마다 승인 대기 작업을 생성합니다. 예약만으로 실제
                  요청이 실행되지는 않습니다.
                </span>
              </div>
              <section className="panel">
                {!records.ready ? (
                  <RecordState records={records} />
                ) : schedules.length ? (
                  schedules.map((s) => (
                    <div className="report-row" key={s.id}>
                      <span className="row-icon">
                        <Clock3 size={18} />
                      </span>
                      <div>
                        <strong>{s.task.name}</strong>
                        <small>
                          {s.interval_hours}시간 간격 · 다음 생성{" "}
                          {date(s.next_at)}
                        </small>
                      </div>
                      <Badge value={s.enabled ? "활성" : "일시 중지"} />
                      <button
                        disabled={busy || !canOperate}
                        onClick={async () => {
                          await act("/schedules/" + s.id + "/toggle");
                        }}
                      >
                        {s.enabled ? "일시 중지" : "재개"}
                      </button>
                    </div>
                  ))
                ) : (
                  <Empty
                    title="표시할 예약이 없습니다"
                    description="매일 또는 매주 필요한 검증 계획을 자동으로 준비하세요."
                  />
                )}
              </section>
            </>
          )}

          {page === "notes" && (
            <>
              <Toolbar
                search={search}
                setSearch={setSearch}
                placeholder="노트 제목 또는 내용으로 검색"
                count={records.total}
                error={records.error}
                loading={!records.ready && records.loading}
              />
              <div className="notes-grid">
                {!records.ready ? (
                  <RecordState records={records} />
                ) : notes.length ? (
                  notes.map((n) => (
                    <section className="panel note-card" key={n.id}>
                      <div className="note-heading">
                        <BookOpen size={18} />
                        <button
                          className="icon-button"
                          aria-label={n.title + " 삭제"}
                          disabled={busy || !canOperate}
                          onClick={async () => {
                            await act(
                              "/notes/" + n.id,
                              "DELETE",
                              undefined,
                              "노트를 삭제했습니다.",
                            );
                          }}
                        >
                          <Trash2 size={15} />
                        </button>
                      </div>
                      <h3>{n.title}</h3>
                      <p>{n.content}</p>
                      <small>{date(n.created_at)}</small>
                    </section>
                  ))
                ) : (
                  <section className="panel">
                    <Empty
                      title={
                        search
                          ? "검색 결과가 없습니다"
                          : "표시할 노트가 없습니다"
                      }
                      description="검증 메모와 운영 지식을 저장하세요. 인증정보는 기록하지 마세요."
                      action={
                        <button
                          disabled={!canOperate}
                          onClick={() => openModal("note")}
                        >
                          <Plus size={15} />
                          노트 작성
                        </button>
                      }
                    />
                  </section>
                )}
              </div>
            </>
          )}

          {page === "agents" && (
            <>
              <div className="agent-grid">
                {settings?.agents.map((a, i) => (
                  <section className="panel agent-card" key={a.id}>
                    <div className="agent-top">
                      <span className={"agent-symbol a" + i}>
                        {i === 0 ? (
                          <GitBranch />
                        ) : i === 1 ? (
                          <Terminal />
                        ) : (
                          <RefreshCw />
                        )}
                      </span>
                      <Badge value="등록됨" />
                    </div>
                    <h3>{a.name}</h3>
                    <p>{a.role}</p>
                    <div className="agent-foot">
                      <span>
                        {a.id === "planner"
                          ? "규칙 기반 / 선택적 LLM"
                          : "검토된 도구 실행"}
                      </span>
                      <ShieldCheck size={15} />
                    </div>
                  </section>
                ))}
              </div>
              <section className="panel">
                <div className="panel-head">
                  <h3>
                    검증 도구 레지스트리 <span>{tools.length}</span>
                  </h3>
                  <span className="subtle">
                    명령 실행 없이 검증 가능한 도구
                  </span>
                </div>
                {tools.map((t) => (
                  <div className="tool-row" key={t.id}>
                    <span className="row-icon">
                      <Code2 size={17} />
                    </span>
                    <div>
                      <strong>
                        {t.name}
                        <code>{t.id}</code>
                      </strong>
                      <small>{t.description}</small>
                    </div>
                    <span className="tool-category">{t.category}</span>
                    <Badge value={t.risk} />
                  </div>
                ))}
              </section>
            </>
          )}

          {page === "users" && canApprove && auth.user && (
            <UserPanel
              currentUser={auth.user}
              onSessionChanged={() => {
                setOverviewLoaded(false);
                setAuth({ setup_required: false, authenticated: false });
              }}
            />
          )}

          {page === "settings" && settings && (
            <>
              <PasswordPanel
                onChanged={() => {
                  setOverviewLoaded(false);
                  setAuth({ setup_required: false, authenticated: false });
                }}
              />
              <RuntimePanel />
              <section className="panel settings-panel">
                <div className="panel-head">
                  <h3>실행 정책</h3>
                  <Badge value="서버 설정" />
                </div>
                {[
                  ["버전", settings.version],
                  [
                    "실습 모드",
                    settings.lab_mode
                      ? "활성 · 사설 주소 검증 허용"
                      : "비활성 · 공개 주소만 검증",
                  ],
                  ["자산별 HTTP 요청 예산", settings.request_budget + "회"],
                  ["작업별 최대 Worker", settings.max_workers + "개"],
                  ["실행 도구", "등록된 읽기 전용 검증 도구"],
                  ["세션", "8시간 · HttpOnly · SameSite=Strict"],
                ].map(([label, value]) => (
                  <div className="setting-row" key={label}>
                    <span>{label}</span>
                    <strong>{value}</strong>
                  </div>
                ))}
              </section>
              <section className="panel settings-panel">
                <div className="panel-head">
                  <h3>선택적 LLM 연결</h3>
                  <Badge
                    value={
                      settings.llm_configured ? "연결 설정됨" : "규칙 기반 모드"
                    }
                  />
                </div>
                <div className="setting-row">
                  <span>모델</span>
                  <strong>{settings.llm_model || "설정되지 않음"}</strong>
                </div>
                <div className="setting-description">
                  <p>
                    LLM은 승인된 도구의 실행 순서를 제안합니다. 응답 본문·테스트
                    계정·쿠키는 전달하지 않습니다. 목표와 자산 이름은 제공자에게
                    전송됩니다.
                  </p>
                  <pre>
                    AEGIS_LLM_API_KEY=…{`\n`}AEGIS_LLM_MODEL=…{`\n`}
                    AEGIS_LLM_BASE_URL=https://provider.example/v1
                  </pre>
                  <p>
                    서버 환경변수를 설정하고 재시작하세요. 키는 브라우저에
                    반환하거나 데이터베이스에 저장하지 않습니다.
                  </p>
                </div>
              </section>
            </>
          )}
          <footer className="page-footer">
            <span>
              <Shield size={13} /> Open Aegis · Evidence-first security
            </span>
            <span>SELF-HOSTED / v{settings?.version || "0.1.0"}</span>
          </footer>
        </div>
      </main>
      {toast && (
        <div className="toast" role="status">
          <CheckCircle2 size={17} />
          {toast}
        </div>
      )}

      {modal && (
        <Modal
          title={
            modal === "asset"
              ? editingAsset
                ? "검증 자산 수정"
                : "검증 자산 등록"
              : modal === "task"
                ? page === "schedules"
                  ? "반복 검증 예약"
                  : "새 검증 계획"
                : modal === "import"
                  ? "JSON 자산 가져오기"
                  : "워크스페이스 노트"
          }
          subtitle={
            modal === "asset"
              ? editingAsset
                ? "수정하면 기존 승인 대기 계획을 새로 만들어야 합니다. 검증 이력이 있는 주소는 변경할 수 없습니다."
                : "주소의 origin과 경로가 검증 범위가 됩니다."
              : modal === "task"
                ? "계획을 만든 후 실행 승인을 진행합니다."
                : undefined
          }
          onClose={closeModal}
        >
          <form onSubmit={submitForm}>
            {modal === "asset" && (
              <>
                <div className="form-grid">
                  <label>
                    자산 이름
                    <input
                      name="name"
                      defaultValue={editingAsset?.name}
                      maxLength={100}
                      required
                      placeholder="예: 고객 포털"
                    />
                  </label>
                  <label>
                    유형
                    <select
                      name="type"
                      defaultValue={editingAsset?.type || "web"}
                    >
                      <option value="web">웹 애플리케이션</option>
                      <option value="api">API</option>
                      <option value="service">서비스</option>
                    </select>
                  </label>
                </div>
                <label>
                  검증 주소
                  <input
                    name="url"
                    defaultValue={editingAsset?.url}
                    type="url"
                    required
                    placeholder="https://your-service.example/"
                  />
                </label>
                <div className="form-grid">
                  <label>
                    담당자
                    <input
                      name="owner"
                      defaultValue={editingAsset?.owner}
                      maxLength={100}
                      placeholder="예: 플랫폼팀"
                    />
                  </label>
                  <label>
                    태그
                    <input
                      name="tags"
                      defaultValue={editingAsset?.tags.join(", ")}
                      placeholder="production, customer"
                    />
                  </label>
                </div>
                <details className="form-details">
                  <summary>API 권한 규칙 설정 (선택)</summary>
                  <p>
                    GET 전용 규칙입니다. 인증 값은 서버의 AEGIS_TEST_*
                    환경변수로 연결하세요.
                  </p>
                  <textarea
                    name="rules"
                    defaultValue={
                      editingAsset
                        ? JSON.stringify(
                            editingAsset.authorization_rules,
                            null,
                            2,
                          )
                        : ""
                    }
                    rows={6}
                    placeholder={
                      '[{"path":"/api/account","role":"anonymous","expected_allowed":false,"credential_env":""}]'
                    }
                  />
                </details>
                <label className="checkbox-label">
                  <input name="authorized" type="checkbox" required />이 자산에
                  대한 검증 권한이 있으며 등록 범위를 확인했습니다.
                </label>
              </>
            )}
            {modal === "task" && (
              <>
                <label>
                  작업 이름
                  <input
                    name="name"
                    maxLength={120}
                    required
                    placeholder="예: 고객 포털 배포 전 검증"
                  />
                </label>
                <label>
                  검증 목표
                  <textarea
                    name="goal"
                    rows={2}
                    maxLength={2000}
                    defaultValue="등록된 자산의 보안 설정과 접근 권한을 검증합니다."
                  />
                </label>
                <AssetPicker initialId={taskAssetId} />
                <fieldset>
                  <legend>검증 도구</legend>
                  <div className="check-grid">
                    {tools.map((t) => (
                      <label className="checkbox-label" key={t.id}>
                        <input
                          type="checkbox"
                          name="check"
                          value={t.id}
                          defaultChecked
                        />
                        {t.name}
                      </label>
                    ))}
                  </div>
                </fieldset>
                <div className="form-grid">
                  <label>
                    Planner
                    <select name="planner">
                      <option value="rules">규칙 기반</option>
                      <option value="ai">AI 계획 (LLM 설정 필요)</option>
                    </select>
                  </label>
                  <label>
                    병렬 Worker
                    <select name="workers" defaultValue="3">
                      {[1, 2, 3, 4].map((n) => (
                        <option value={n} key={n}>
                          {n}개
                        </option>
                      ))}
                    </select>
                  </label>
                </div>
                {page === "schedules" && (
                  <label>
                    검증 계획 생성 간격
                    <select name="interval">
                      <option value="24">매일 · 24시간</option>
                      <option value="168">매주 · 168시간</option>
                      <option value="1">매시간</option>
                    </select>
                  </label>
                )}
              </>
            )}
            {modal === "import" && (
              <>
                <p className="subtle">
                  동일한 주소는 중복 등록할 수 없습니다. 모든 자산에 authorized:
                  true가 필요합니다.
                </p>
                <label>
                  자산 JSON 배열
                  <textarea
                    name="json"
                    rows={12}
                    required
                    placeholder={
                      '[{"name":"Customer portal","url":"https://your-service.example/","type":"web","authorized":true}]'
                    }
                  />
                </label>
              </>
            )}
            {modal === "note" && (
              <>
                <label>
                  제목
                  <input
                    name="title"
                    maxLength={120}
                    required
                    placeholder="예: 고객 포털 검증 메모"
                  />
                </label>
                <label>
                  내용
                  <textarea
                    name="content"
                    rows={9}
                    maxLength={10000}
                    required
                    placeholder="확인한 내용과 다음 작업을 기록하세요."
                  />
                </label>
              </>
            )}
            {formError && (
              <p className="form-error" role="alert">
                {formError}
              </p>
            )}
            <div className="modal-actions">
              <button type="button" onClick={closeModal}>
                취소
              </button>
              <button
                className="primary"
                disabled={busy || !canOperate}
                type="submit"
              >
                {busy
                  ? "저장 중…"
                  : modal === "task"
                    ? "계획 만들기"
                    : "저장하기"}
                <ArrowRight size={15} />
              </button>
            </div>
          </form>
        </Modal>
      )}

      {archivingAsset && (
        <Modal
          title={archivingAsset.archived_at ? "자산 복원" : "자산 보관"}
          subtitle={archivingAsset.name}
          onClose={() => setArchivingAsset(null)}
        >
          <p className="remediation">
            {archivingAsset.archived_at
              ? "자산을 활성 목록으로 복원합니다. 기존 예약은 직접 재개해야 하며, 새 검증 계획과 승인이 필요합니다."
              : "증거와 검증 이력은 유지합니다. 이 자산을 포함한 예약은 중지되고, 기존 승인 대기 계획은 실행할 수 없게 됩니다."}
          </p>
          <div className="modal-actions">
            <button onClick={() => setArchivingAsset(null)}>취소</button>
            <button
              className="primary"
              disabled={busy || !canOperate}
              onClick={async () => {
                const result = await act(
                  "/assets/" + archivingAsset.id + "/archive",
                  "POST",
                  { archived: !archivingAsset.archived_at },
                  archivingAsset.archived_at
                    ? "자산을 복원했습니다."
                    : "자산을 보관했습니다.",
                );
                if (result) setArchivingAsset(null);
              }}
            >
              {archivingAsset.archived_at ? "복원하기" : "보관하기"}
            </button>
          </div>
        </Modal>
      )}

      {selectedTask && (
        <Modal
          title={selectedTask.name}
          subtitle={selectedTask.goal}
          onClose={closeTask}
        >
          <div className="detail-summary">
            <Badge value={selectedTask.status} />
            <span>
              {selectedTask.done} / {selectedTask.asset_ids.length} 자산 처리
            </span>
            <span>{selectedTask.errors}개 오류</span>
          </div>
          {selectedTask.termination_reason && (
            <p className="remediation">
              종료 사유:{" "}
              {{
                timeout: "작업 실행 시간 초과",
                queue_timeout: "대기열 시간 초과",
                operator_stop: "운영자 중지",
                shutdown: "서버 종료",
                internal_error: "내부 오류",
              }[selectedTask.termination_reason] ||
                selectedTask.termination_reason}
            </p>
          )}
          {selectedTask.queue_wait_ms !== undefined && (
            <p className="subtle">
              실행 전 대기: {(selectedTask.queue_wait_ms / 1000).toFixed(1)}초
            </p>
          )}
          {selectedTask.execution_policy && (
            <details>
              <summary>승인한 실행 정책</summary>
              <PolicySummary policy={selectedTask.execution_policy} />
            </details>
          )}
          {selectedTask.retry_of && (
            <p className="subtle">
              원본 작업: {selectedTask.retry_of} · 현재 범위로 만든 재실행 계획
            </p>
          )}
          <h4 className="detail-heading">승인 범위</h4>
          <div className="scope-list">
            {selectedTask.scope_snapshot.map((a) => (
              <code key={a.id}>{a.url}</code>
            ))}
          </div>
          <div className="tags">
            {(selectedTask.plan || selectedTask.checks).map((c) => (
              <span key={c}>{tools.find((t) => t.id === c)?.name || c}</span>
            ))}
          </div>
          <h4 className="detail-heading">도구별 실행 결과</h4>
          {taskDetail && (
            <CoverageTable
              rows={taskDetail.coverage}
              assets={selectedTask.scope_snapshot}
              tools={tools}
            />
          )}
          <h4 className="detail-heading">
            실행 기록 <span>{taskDetail?.events.length || 0}</span>
          </h4>
          <div className="execution-log">
            {taskDetail?.events.map((e) => (
              <div className={"execution-entry " + e.level} key={e.seq}>
                <span>{date(e.ts)}</span>
                <div>
                  <strong>{e.message}</strong>
                  {Object.keys(e.detail).length > 0 && (
                    <small>{JSON.stringify(e.detail)}</small>
                  )}
                </div>
              </div>
            ))}
          </div>
          <ChatPanel taskId={selectedTask.id} canOperate={canOperate} />
          <div className="modal-actions">
            <a
              className="button"
              href={
                "/api/reports/export?format=markdown&task_id=" + selectedTask.id
              }
              download
            >
              <ArrowDownToLine size={15} />
              보고서
            </a>
            {["failed", "interrupted", "stopped"].includes(
              selectedTask.status,
            ) && (
              <button
                className="primary"
                disabled={busy || !canOperate}
                onClick={async () => {
                  const result = await act(
                    "/tasks/" + selectedTask.id + "/retry",
                    "POST",
                    undefined,
                    "재실행 계획을 만들었습니다. 현재 범위와 정책을 승인하세요.",
                  );
                  if (result) {
                    closeTask();
                    navigate("approvals", true);
                  }
                }}
              >
                <RefreshCw size={15} />
                재실행 계획
              </button>
            )}
            {selectedTask.status === "pending" ? (
              <button
                className="primary"
                disabled={busy || !canApprove}
                onClick={async () => {
                  await act("/tasks/" + selectedTask.id + "/approve");
                  closeTask();
                }}
              >
                승인하고 실행
                <Check size={15} />
              </button>
            ) : ["running", "queued", "stopping"].includes(
                selectedTask.status,
              ) ? (
              <button
                className="danger"
                disabled={
                  busy || !canOperate || selectedTask.status === "stopping"
                }
                onClick={() => void act("/tasks/" + selectedTask.id + "/stop")}
              >
                <Square size={14} />
                작업 중지
              </button>
            ) : (
              <button onClick={closeTask}>닫기</button>
            )}
          </div>
        </Modal>
      )}

      {selectedFinding && (
        <Modal
          title={selectedFinding.finding.title}
          subtitle={
            selectedFinding.finding.asset_name +
            " · " +
            confidenceNames[selectedFinding.finding.confidence]
          }
          onClose={closeFinding}
        >
          <div className="detail-summary">
            <Badge value={selectedFinding.finding.severity} />
            <Badge value={selectedFinding.finding.status} />
            <span>{date(selectedFinding.finding.created_at)}</span>
          </div>
          <FindingTriage
            key={`${selectedFinding.finding.id}:${selectedFinding.finding.triage_revision || 1}:${findingReload}`}
            finding={selectedFinding.finding}
            canOperate={canOperate}
            onReload={() => void openFinding(selectedFinding.finding.id, true)}
            onUpdated={(value) => {
              setSelectedFinding((current) =>
                current?.finding.id === value.id
                  ? { ...current, finding: { ...current.finding, ...value } }
                  : current,
              );
              window.dispatchEvent(new Event("aegis-records-changed"));
              void refresh();
            }}
          />
          <h4 className="detail-heading">관찰 증거</h4>
          <pre>{JSON.stringify(selectedFinding.finding.evidence, null, 2)}</pre>
          <h4 className="detail-heading">수정 가이드</h4>
          <p className="remediation">{selectedFinding.finding.remediation}</p>
          <FindingRecords
            key={selectedFinding.finding.id}
            findingId={selectedFinding.finding.id}
            checkNames={Object.fromEntries(
              tools.map((tool) => [tool.id, tool.name]),
            )}
          />
          <div className="modal-actions">
            <button
              className="primary"
              disabled={busy || !canOperate}
              onClick={async () => {
                const result = await act(
                  "/findings/" + selectedFinding.finding.id + "/retest",
                  "POST",
                  undefined,
                  "재검증 계획을 만들었습니다. 범위를 승인하세요.",
                );
                if (result) {
                  closeFinding();
                  navigate("approvals", true);
                }
              }}
            >
              <RefreshCw size={15} />
              재검증 계획
            </button>
          </div>
        </Modal>
      )}
      {trafficDetail && (
        <Modal
          title="HTTP 요청 기록"
          subtitle={trafficDetail.url}
          onClose={closeTraffic}
        >
          <div className="detail-summary">
            <Badge value={trafficDetail.method} />
            <Badge
              value={
                trafficDetail.status
                  ? String(trafficDetail.status)
                  : "연결 실패"
              }
            />
            <span>
              {trafficDetail.elapsed_ms} ms · {trafficDetail.bytes} B
            </span>
          </div>
          <h4 className="detail-heading">응답 헤더</h4>
          <pre>{JSON.stringify(trafficDetail.headers, null, 2)}</pre>
          <h4 className="detail-heading">증거 메타데이터</h4>
          <pre>
            {JSON.stringify(
              {
                address: trafficDetail.address,
                body_sha256: trafficDetail.body_sha256,
                created_at: date(trafficDetail.created_at),
              },
              null,
              2,
            )}
          </pre>
          <p className="subtle">
            본문은 저장하지 않았습니다. 해시는 수신한 최대 128 KiB 본문을
            대상으로 계산합니다.
          </p>
        </Modal>
      )}
    </div>
  );
}
function Toolbar({
  search,
  setSearch,
  placeholder,
  count,
  loading = false,
  error = "",
  children,
}: {
  search: string;
  setSearch: (v: string) => void;
  placeholder: string;
  count: number;
  loading?: boolean;
  error?: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="toolbar">
      <div className="search-input">
        <Search size={16} />
        <input
          aria-label={placeholder}
          placeholder={placeholder}
          value={search}
          maxLength={200}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>
      <span className="subtle">
        {error ? "조회 실패" : loading ? "불러오는 중…" : `${count}개 항목`}
      </span>
      {children}
    </div>
  );
}

function ChatPanel({
  taskId,
  canOperate,
}: {
  taskId: string;
  canOperate: boolean;
}) {
  type Message = {
    id: string;
    role: string;
    content: string;
    finding_ids?: string[];
  };
  const [messages, setMessages] = useState<Message[]>([]),
    [question, setQuestion] = useState(""),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  useEffect(() => {
    api<Message[]>("/tasks/" + taskId + "/messages")
      .then(setMessages)
      .catch((e) => setError(e.message));
  }, [taskId]);
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (busy || !question.trim()) return;
    setBusy(true);
    setError("");
    try {
      await api("/tasks/" + taskId + "/messages", "POST", {
        content: question,
      });
      setMessages(await api("/tasks/" + taskId + "/messages"));
      setQuestion("");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <details className="chat-panel">
      <summary>
        검증 기록에 질문하기 <span>규칙 기반 · 추가 요청 없음</span>
      </summary>
      <div className="chat-messages">
        {messages.length ? (
          messages.map((m) => (
            <div className={"chat-message " + m.role} key={m.id}>
              <small>{m.role === "user" ? "나" : "Evidence Assistant"}</small>
              <p>{m.content}</p>
              {m.finding_ids && m.finding_ids.length > 0 && (
                <small>연결된 발견 사항 {m.finding_ids.length}개</small>
              )}
            </div>
          ))
        ) : (
          <p className="subtle">
            예: “무엇부터 수정하면 되나요?” · “현재 검증 결과를 요약해줘”
          </p>
        )}
      </div>
      <form onSubmit={submit}>
        <label>
          검증 질문
          <input
            maxLength={2000}
            required
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="저장된 검증 기록에 대해 질문하세요"
          />
        </label>
        <button className="primary" disabled={busy || !canOperate}>
          {busy ? "요약 중…" : "질문하기"}
          <ArrowRight size={14} />
        </button>
      </form>
      {error && <p className="form-error">{error}</p>}
    </details>
  );
}

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
