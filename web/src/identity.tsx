import { t as uiText, localizeLabels } from "./i18n-core.ts";
import React, { useCallback, useEffect, useRef, useState } from "react";
import { KeyRound, Plus, UsersRound } from "lucide-react";
import { api, captureSession, expireSession } from "./api";
import Modal from "./components/Modal";

export type User = {
  id: string;
  username: string;
  name: string;
  role: "admin" | "operator" | "viewer";
  disabled: boolean | number;
  created_at: number;
  updated_at: number;
};
export const roleNames = localizeLabels({
  admin: "관리자",
  operator: "운영자",
  viewer: "조회자",
});
const roleDescriptions = localizeLabels({
  admin: "사용자 관리, 실행 승인, 자산과 결과 관리",
  operator: "자산 관리, 검증 계획 작성, 결과 조치와 작업 중지",
  viewer: "자산·기록·증거 조회와 보고서 내보내기",
});

export function UserPanel({
  currentUser,
  onSessionChanged,
}: {
  currentUser: User;
  onSessionChanged: () => void;
}) {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [mode, setMode] = useState<"add" | "edit" | "reset" | null>(null);
  const [selected, setSelected] = useState<User | null>(null);
  const [formError, setFormError] = useState("");
  const [notice, setNotice] = useState("");
  const active = useRef(true);
  const submitting = useRef(false);
  const loadSequence = useRef(0);
  useEffect(() => {
    active.current = true;
    return () => {
      active.current = false;
      loadSequence.current++;
    };
  }, []);
  const load = useCallback(async () => {
    const sequence = ++loadSequence.current;
    const isCurrentSession = captureSession();
    const isCurrent = () =>
      active.current && isCurrentSession() && sequence === loadSequence.current;
    setLoading(true);
    try {
      const records = await api<User[]>("/users");
      if (!isCurrent()) return;
      setUsers(records);
      setError("");
    } catch (e) {
      if (isCurrent()) setError((e as Error).message);
    } finally {
      if (isCurrent()) setLoading(false);
    }
  }, []);
  useEffect(() => {
    void load();
  }, [load]);
  const close = useCallback(() => {
    if (!busy) setMode(null);
  }, [busy]);
  function open(value: typeof mode, user: User | null = null) {
    setSelected(user);
    setMode(value);
    setFormError("");
    setNotice("");
  }
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting.current) return;
    submitting.current = true;
    const isCurrentSession = captureSession();
    const isCurrent = () => active.current && isCurrentSession();
    setBusy(true);
    setFormError("");
    const form = new FormData(event.currentTarget);
    try {
      if (mode === "add") {
        await api("/users", "POST", {
          username: form.get("username"),
          name: form.get("name"),
          role: form.get("role"),
          password: form.get("password"),
        });
      } else if (mode === "edit" && selected) {
        const body = {
          expected_updated_at: selected.updated_at,
          name: form.get("name"),
          role: form.get("role"),
          disabled: form.get("disabled") === "on",
        };
        await api("/users/" + selected.id, "PATCH", body);
        if (!isCurrent()) return;
        if (
          selected.id === currentUser.id &&
          (body.role !== currentUser.role || body.disabled)
        ) {
          expireSession(isCurrentSession);
          onSessionChanged();
          return;
        }
      } else if (mode === "reset" && selected) {
        await api("/users/" + selected.id + "/password", "POST", {
          password: form.get("password"),
        });
        if (!isCurrent()) return;
        if (selected.id === currentUser.id) {
          expireSession(isCurrentSession);
          onSessionChanged();
          return;
        }
      }
      if (!isCurrent()) return;
      setMode(null);
      setNotice(uiText("사용자 설정을 적용했습니다."));
      await load();
    } catch (e) {
      if (isCurrent()) setFormError((e as Error).message);
    } finally {
      submitting.current = false;
      if (active.current) setBusy(false);
    }
  }
  return (
    <>
      <div className="role-grid">
        {Object.entries(roleNames).map(([role, name]) => (
          <section className="panel role-card" key={role}>
            <UsersRound size={22} />
            <h3>{name}</h3>
            <p>{roleDescriptions[role as User["role"]]}</p>
          </section>
        ))}
      </div>
      <section className="panel">
        <div className="panel-head">
          <h3>
            {uiText("워크스페이스 사용자 ")}<span>{users.length}</span>
          </h3>
          <button className="primary" onClick={() => open("add")}>
            <Plus size={16} />
            {uiText("사용자 추가")}</button>
        </div>
        <p className="identity-policy">
          {uiText("모든 사용자는 같은 워크스페이스를 공유합니다. 관리자만 검증 실행을 승인할 수 있습니다. 권한·계정 상태·비밀번호 변경은 기존 세션을 만료시킵니다.")}</p>
        {error && (
          <p className="form-error" role="alert">
            {error}
            <button onClick={() => void load()}>{uiText("다시 조회")}</button>
          </p>
        )}
        {notice && (
          <p className="identity-notice" role="status">
            {notice}
          </p>
        )}
        {loading ? (
          <p className="quiet-state">{uiText("사용자를 불러오는 중…")}</p>
        ) : (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>{uiText("사용자")}</th>
                  <th>{uiText("역할")}</th>
                  <th>{uiText("상태")}</th>
                  <th>{uiText("관리")}</th>
                </tr>
              </thead>
              <tbody>
                {users.map((user) => (
                  <tr key={user.id}>
                    <td>
                      <strong>{user.name}</strong>
                      <small className="identity-username">
                        {user.username}
                        {user.id === currentUser.id ? uiText(" · 내 계정") : ""}
                      </small>
                    </td>
                    <td>{roleNames[user.role]}</td>
                    <td>
                      <span
                        className={
                          "badge " + (user.disabled ? "rejected" : "completed")
                        }
                      >
                        {user.disabled ? uiText("비활성") : uiText("활성")}
                      </span>
                    </td>
                    <td>
                      <div className="identity-actions">
                        <button
                          aria-label={user.username + uiText(" 사용자 수정")}
                          onClick={() => open("edit", user)}
                        >
                          {uiText("수정")}</button>
                        <button
                          aria-label={user.username + uiText(" 비밀번호 재설정")}
                          onClick={() => open("reset", user)}
                        >
                          <KeyRound size={15} />
                          {uiText("재설정")}</button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
      {mode && (
        <Modal
          title={
            mode === "add"
              ? uiText("사용자 추가")
              : mode === "edit"
                ? uiText("사용자 수정")
                : uiText("비밀번호 재설정")
          }
          subtitle={
            selected
              ? selected.username
              : uiText("사용자에게 초기 비밀번호를 직접 전달하세요.")
          }
          onClose={close}
        >
          <form onSubmit={submit}>
            <fieldset
              disabled={busy}
              className="identity-form-fields"
              aria-label={uiText("사용자 설정 입력")}
            >
              {mode === "add" && (
                <label>
                  {uiText("사용자 이름")}<input
                    name="username"
                    pattern="[a-zA-Z0-9_.-]+"
                    maxLength={64}
                    required
                    autoComplete="off"
                    placeholder={uiText("예: security.operator")}
                  />
                </label>
              )}
              {mode !== "reset" && (
                <>
                  <label>
                    {uiText("표시 이름")}<input
                      name="name"
                      defaultValue={selected?.name}
                      maxLength={100}
                      required
                    />
                  </label>
                  <label>
                    {uiText("역할")}<select
                      name="role"
                      defaultValue={selected?.role || "viewer"}
                    >
                      {Object.entries(roleNames).map(([role, name]) => (
                        <option key={role} value={role}>
                          {name}
                        </option>
                      ))}
                    </select>
                  </label>
                </>
              )}
              {mode === "edit" && (
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    name="disabled"
                    defaultChecked={!!selected?.disabled}
                  />
                  {uiText("계정 비활성화")}</label>
              )}
              {mode !== "edit" && (
                <label>
                  {mode === "add" ? uiText("초기 비밀번호") : uiText("새 비밀번호")}
                  <input
                    type="password"
                    name="password"
                    minLength={12}
                    maxLength={256}
                    required
                    autoComplete="new-password"
                  />
                </label>
              )}
              {formError && (
                <p className="form-error" role="alert">
                  {formError}
                </p>
              )}
              <div className="modal-actions">
                <button type="button" disabled={busy} onClick={close}>
                  {uiText("취소")}</button>
                <button className="primary" disabled={busy} type="submit">
                  {busy ? uiText("적용 중…") : uiText("적용하기")}
                </button>
              </div>
            </fieldset>
          </form>
        </Modal>
      )}
    </>
  );
}

export function PasswordPanel({ onChanged }: { onChanged: () => void }) {
  const active = useRef(true);
  const submitting = useRef(false);
  useEffect(() => {
    active.current = true;
    return () => {
      active.current = false;
    };
  }, []);
  const [open, setOpen] = useState(false),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const close = useCallback(() => {
    if (!busy) setOpen(false);
  }, [busy]);
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting.current) return;
    const form = new FormData(event.currentTarget);
    if (form.get("new_password") !== form.get("confirm_password")) {
      setError(uiText("새 비밀번호가 일치하지 않습니다."));
      return;
    }
    setBusy(true);
    submitting.current = true;
    setError("");
    try {
      await api("/auth/password", "POST", {
        current_password: form.get("current_password"),
        new_password: form.get("new_password"),
      });
      if (active.current) onChanged();
    } catch (e) {
      if (active.current) setError((e as Error).message);
    } finally {
      submitting.current = false;
      if (active.current) setBusy(false);
    }
  }
  return (
    <>
      <section className="panel settings-panel">
        <div className="panel-head">
          <h3>{uiText("내 계정")}</h3>
          <button
            onClick={() => {
              setError("");
              setOpen(true);
            }}
          >
            <KeyRound size={16} />
            {uiText("비밀번호 변경")}</button>
        </div>
        <p className="identity-policy">
          {uiText("변경하면 모든 기기의 기존 세션이 만료되고 새 비밀번호로 다시 로그인해야 합니다.")}</p>
      </section>
      {open && (
        <Modal title={uiText("내 비밀번호 변경")} onClose={close}>
          <form onSubmit={submit}>
            <fieldset
              disabled={busy}
              className="identity-form-fields"
              aria-label={uiText("비밀번호 변경 입력")}
            >
              <label>
                {uiText("현재 비밀번호")}<input
                  name="current_password"
                  type="password"
                  required
                  maxLength={256}
                  autoComplete="current-password"
                />
              </label>
              <label>
                {uiText("새 비밀번호")}<input
                  name="new_password"
                  type="password"
                  required
                  minLength={12}
                  maxLength={256}
                  autoComplete="new-password"
                />
              </label>
              <label>
                {uiText("새 비밀번호 확인")}<input
                  name="confirm_password"
                  type="password"
                  required
                  minLength={12}
                  maxLength={256}
                  autoComplete="new-password"
                />
              </label>
              {error && (
                <p className="form-error" role="alert">
                  {error}
                </p>
              )}
              <div className="modal-actions">
                <button type="button" disabled={busy} onClick={close}>
                  {uiText("취소")}</button>
                <button type="submit" className="primary" disabled={busy}>
                  {busy ? uiText("변경 중…") : uiText("변경하기")}
                </button>
              </div>
            </fieldset>
          </form>
        </Modal>
      )}
    </>
  );
}
