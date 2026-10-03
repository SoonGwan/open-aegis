const frame = document.querySelector("iframe");
const metrics = document.querySelector("#metrics");
for (const button of document.querySelectorAll("[data-width]")) {
  button.addEventListener("click", () => {
    frame.style.width = `${button.dataset.width}px`;
    metrics.textContent = "너비 변경 후 측정 중";
  });
}
window.addEventListener("message", (event) => {
  if (event.origin === location.origin && event.source === frame.contentWindow && event.data?.type === "responsive-metrics")
    metrics.textContent = JSON.stringify(event.data, null, 2);
});
