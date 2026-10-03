setInterval(() => {
  const d = document.documentElement,
    dialog = document.querySelector("[role=dialog]"),
    scope = dialog || document.querySelector("main");
  const outside = [],
    contained = [];
  for (const e of scope?.querySelectorAll("button,input,select,h1,section") ||
    []) {
    const r = e.getBoundingClientRect();
    if (
      !r.width ||
      e.closest("[inert]") ||
      !(r.right > d.clientWidth + 1 || r.left < 0)
    )
      continue;
    const item = {
      tag: e.tagName,
      label: (
        e.textContent ||
        e.getAttribute("aria-label") ||
        e.getAttribute("placeholder") ||
        ""
      ).slice(0, 60),
      width: Math.round(r.width),
    };
    let parent = e.parentElement,
      bounded = false;
    while (parent && parent !== document.body) {
      const x = getComputedStyle(parent).overflowX;
      if (
        ["auto", "scroll"].includes(x) &&
        parent.scrollWidth > parent.clientWidth
      ) {
        bounded = true;
        break;
      }
      parent = parent.parentElement;
    }
    (bounded ? contained : outside).push(item);
  }
  parent.postMessage(
    {
      type: "responsive-metrics",
      viewport: innerWidth,
      rootClient: d.clientWidth,
      rootScroll: d.scrollWidth,
      heading: document.querySelector("h1")?.textContent,
      modal: dialog?.getBoundingClientRect().width,
      overflow: outside.slice(0, 8),
      containedOverflow: contained.length,
    },
    location.origin,
  );
}, 500);
