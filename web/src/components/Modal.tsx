import { X } from "lucide-react";
import React, { useEffect, useLayoutEffect, useRef, useId } from "react";

function focusable(root: HTMLElement | null, reverse = false): HTMLElement[] {
  if (!root) return [];
  const ordered = Array.from(
    root.querySelectorAll<HTMLElement>(
      "button,input,textarea,select,a[href],summary,[tabindex],[contenteditable='true']",
    ),
  )
    .filter(
      (el) =>
        el.tabIndex >= 0 &&
        !el.matches(":disabled") &&
        !el.closest("[inert],[hidden],[aria-hidden='true']") &&
        el.getClientRects().length > 0 &&
        !["hidden", "collapse"].includes(getComputedStyle(el).visibility),
    )
    .sort(
      (a, b) =>
        (a.tabIndex > 0 ? a.tabIndex : Infinity) -
        (b.tabIndex > 0 ? b.tabIndex : Infinity),
    );
  // Native radio groups have one Tab stop. All members expose tabIndex=0,
  // so treating each as a boundary can let Tab escape from the checked member.
  const active = document.activeElement;
  return ordered.filter((el) => {
    if (!(el instanceof HTMLInputElement) || el.type !== "radio" || !el.name)
      return true;
    const group = ordered.filter(
      (candidate): candidate is HTMLInputElement =>
        candidate instanceof HTMLInputElement &&
        candidate.type === "radio" &&
        candidate.name === el.name &&
        candidate.form === el.form &&
        candidate.getRootNode() === el.getRootNode(),
    );
    const current = group.find((member) => member === active);
    const checked = group.find((member) => member.checked);
    const entry = reverse ? group[group.length - 1] : group[0];
    return el === (current || checked || entry);
  });
}

export default function Modal({
  title,
  subtitle,
  children,
  onClose,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  onClose: () => void;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const close = useRef(onClose);
  const titleId = useId();
  const subtitleId = useId();
  useLayoutEffect(() => {
    close.current = onClose;
  }, [onClose]);
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    const restored: { element: HTMLElement; inert: boolean }[] = [];
    let node = ref.current?.parentElement;
    // A dialog may live inside a page component. Disable every sibling subtree
    // along its ancestor path, never an ancestor containing the dialog itself.
    while (node?.parentElement) {
      for (const sibling of Array.from(node.parentElement.children)) {
        if (sibling !== node && sibling instanceof HTMLElement) {
          restored.push({ element: sibling, inert: sibling.inert });
          sibling.inert = true;
        }
      }
      if (node.parentElement === document.body) break;
      node = node.parentElement;
    }
    const oldOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    (focusable(ref.current)[0] || ref.current)?.focus();
    const key = (e: KeyboardEvent) => {
      if (e.defaultPrevented) return;
      if (e.key === "Escape") {
        e.preventDefault();
        e.stopPropagation();
        close.current();
      }
      if (e.key === "Tab") {
        const list = focusable(ref.current, e.shiftKey);
        const first = list[0],
          last = list[list.length - 1];
        if (!list.length) {
          e.preventDefault();
          ref.current?.focus();
        } else if (!list.includes(document.activeElement as HTMLElement)) {
          e.preventDefault();
          (e.shiftKey ? last : first)?.focus();
        } else if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last?.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first?.focus();
        }
      }
    };
    document.addEventListener("keydown", key);
    return () => {
      document.removeEventListener("keydown", key);
      for (const { element, inert } of restored) element.inert = inert;
      document.body.style.overflow = oldOverflow;
      if (previous?.isConnected && !previous.closest("[inert]"))
        previous.focus();
      else
        document
          .querySelector<HTMLElement>(
            "main button:not(:disabled),main a[href],main input:not(:disabled)",
          )
          ?.focus();
    };
  }, []);
  return (
    <div
      className="modal-backdrop"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        ref={ref}
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-label={title}
        aria-labelledby={titleId}
        aria-describedby={subtitle ? subtitleId : undefined}
        tabIndex={-1}
      >
        <div className="modal-head">
          <div>
            <h2 id={titleId}>{title}</h2>
            {subtitle && <p id={subtitleId}>{subtitle}</p>}
          </div>
          <button className="icon-button" onClick={onClose} aria-label="닫기">
            <X size={20} />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
