// =======================
// ELEMENTS
// =======================
const eyes = document.querySelectorAll(".eye");
const mouth = document.getElementById("mouth");
const face = document.querySelector(".face");

// =======================
// STATE
// =======================
let isSpeaking = false;
let blinkEnabled = true;

// =======================
// MOUTH CONFIG
// =======================
const MOUTH_CLOSED = 0.2;
const MOUTH_OPEN = 1.4;

// =======================
// BLINK SYSTEM
// =======================
function blink() {
  eyes.forEach(eye => {
    eye.classList.add("blink");

    setTimeout(() => {
      eye.classList.remove("blink");
    }, 150);
  });
}

function startBlinkLoop() {
  setInterval(() => {
    if (!blinkEnabled) return;

    if (!isSpeaking && Math.random() > 0.6) {
      blink();
    }
  }, 2000);
}

// =======================
// MOUTH SYSTEM
// =======================
function setSpeaking(state) {
  isSpeaking = state;

  if (!state) {
    // force clean idle state
    mouth.style.transform =
      `translateX(-50%) scaleY(${MOUTH_CLOSED})`;
  }
}

function setMouthIntensity(level) {
  // if not speaking, always stay closed
  if (!isSpeaking) {
    mouth.style.transform =
      `translateX(-50%) scaleY(${MOUTH_CLOSED})`;
    return;
  }

  // add slight organic variation
  const jitter = (Math.random() - 0.5) * 0.05;

  const scaleY =
    MOUTH_CLOSED +
    level * (MOUTH_OPEN - MOUTH_CLOSED) +
    jitter;

  mouth.style.transform =
    `translateX(-50%) scaleY(${scaleY})`;
}

// =======================
// EXPRESSIONS (future-ready)
// =======================
function setExpression(name) {
  document.body.dataset.expression = name;
}

// =======================
// DEMO SPEECH
// =======================
function speakDemo() {
  setSpeaking(true);

  let i = 0;

  const interval = setInterval(() => {
    const level = Math.random(); // fake audio energy

    setMouthIntensity(level);

    i++;

    if (i > 25) {
      clearInterval(interval);
      setSpeaking(false);

      // snap back to closed mouth
      setMouthIntensity(0);
    }
  }, 100);
}

// =======================
// INIT
// =======================
function init() {
  startBlinkLoop();

  setExpression("neutral");

  // click face to trigger speech test
  face.addEventListener("click", speakDemo);
}

init();
