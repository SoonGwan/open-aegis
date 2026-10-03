const frame = document.querySelector("iframe");
function show(url) {
  document.querySelector("#metrics").textContent = "불러오는 중…";
  frame.src = url;
}
const config = JSON.parse(document.querySelector("#review-config").textContent);
document.querySelectorAll("[data-width]").forEach((button) => {
  button.onclick = () => {
    frame.style.width = button.dataset.width + "px";
  };
});
document.querySelectorAll("[data-page]").forEach((button) => {
  button.onclick = () => {
    show("/?page=" + button.dataset.page);
  };
});
for (const [name, page] of [
  ["finding", "findings"],
  ["task", "tasks"],
]) {
  const button = document.querySelector("#" + name);
  button.disabled = !config[name];
  button.onclick = () => {
    const query = new URLSearchParams({
      page,
      detail: name,
      detail_id: config[name],
    });
    show("/?" + query);
  };
}
window.addEventListener("message", (event) => {
  if (
    event.origin !== location.origin ||
    event.source !== frame.contentWindow ||
    event.data?.type !== "responsive-metrics"
  )
    return;
  document.querySelector("#metrics").textContent = JSON.stringify(
    event.data,
    null,
    2,
  );
  document.querySelector("p").textContent =
    event.data.viewport +
    " × 844 CSS 픽셀 · 실제 앱 · 검수용 프레임 허용 서버 · 터치/기기 에뮬레이션 아님";
});
