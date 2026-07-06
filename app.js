const eyes = document.getElementById("eyes");
const mouth = document.getElementById("mouth");

let blinkEnabled = true;
let talking = false;

/* -----------------------
   EYES SYSTEM
------------------------ */

function setEyes(state) {
  eyes.className = "";

  if (state === "open") eyes.classList.add("eyes-open");
  if (state === "closed") eyes.classList.add("eyes-closed");
  if (state === "happy") eyes.classList.add("eyes-happy");
}

function blink() {
  if (!blinkEnabled) return;

  setEyes("closed");

  setTimeout(() => {
    setEyes("open");
  }, 120);
}

/* random blinking loop */
setInterval(() => {
  if (Math.random() < 0.12) blink();
}, 1800);

/* -----------------------
   MOUTH SYSTEM
------------------------ */

function setMouth(v) {
  const scale = 0.2 + v * 1.2;
  mouth.style.transform = `translateX(-50%) scaleY(${scale})`;
}

/* fake speech engine */
function startTalking() {
  talking = true;
  blinkEnabled = false;

  const interval = setInterval(() => {
    if (!talking) {
      clearInterval(interval);
      return;
    }

    setMouth(Math.random());
  }, 70);
}

function stopTalking() {
  talking = false;
  blinkEnabled = true;
  setMouth(0);
}

/* -----------------------
   DEMO LOOP
------------------------ */

setInterval(() => {
  startTalking();

  setTimeout(() => {
    stopTalking();
  }, 2500);

}, 5000);

/* click test */
document.body.addEventListener("click", () => {
  startTalking();
  setTimeout(stopTalking, 2000);
});
