/* ==========================
   APP
========================== */

window.onload = function () {
  setPose("neutral");

  startBlinking();
  startIdle();

  startRenderLoop();

  document.querySelectorAll("[data-expression]").forEach(function (button) {
    button.addEventListener("click", function () {
      const expression = button.getAttribute("data-expression");
      setPose(expression);
    });
  });

  const talkButton = document.querySelector("#talkTest");
  const speechText = document.querySelector("#speechText");

  if (talkButton && speechText) {
    talkButton.addEventListener("click", function () {
      sayText(speechText.value);
    });
  }
};

function startRenderLoop() {
  function animate() {
    renderCharacter();
    requestAnimationFrame(animate);
  }

  animate();
}
const button = document.getElementById("standbyButton");
button.addEventListener("click", function () {
  toggleStandby();

  button.textContent = isStandby() ? "Wake Up" : "Standby";
});

const viewportDebug = document.createElement("div");

viewportDebug.style.position = "fixed";
viewportDebug.style.top = "10px";
viewportDebug.style.left = "10px";
viewportDebug.style.zIndex = "99999";
viewportDebug.style.background = "rgba(0,0,0,0.8)";
viewportDebug.style.color = "white";
viewportDebug.style.padding = "8px 12px";
viewportDebug.style.fontFamily = "monospace";
viewportDebug.style.fontSize = "18px";

function updateViewportDebug() {
  viewportDebug.textContent =
    `Viewport: ${window.innerWidth} × ${window.innerHeight} | ` +
    `Screen: ${screen.width} × ${screen.height} | ` +
    `DPR: ${window.devicePixelRatio}`;
}

document.body.appendChild(viewportDebug);

updateViewportDebug();

window.addEventListener("resize", updateViewportDebug);
