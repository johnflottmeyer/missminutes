// speech.js

let speechTimer = null;
let isSpeaking = false;

function setMouthSpeech(amount) {
    const character = document.querySelector("#character");
    if (!character) return;

    character.style.setProperty("--mouth-speech", amount);
}

function startSpeech() {
    if (isSpeaking) return;

    stopIdle();

    isSpeaking = true;

    speechTimer = setInterval(function () {
        const shapes = [0.05, 0.15, 0.35, 0.55, 0.25];
        const open = shapes[Math.floor(Math.random() * shapes.length)];

        setMouthSpeech(open);
    }, 85);
}

function stopSpeech() {
    isSpeaking = false;

    clearInterval(speechTimer);
    speechTimer = null;

    setMouthSpeech(0);

    startIdle();
}

function speakTest(duration) {
    duration = duration || 3000;

    startSpeech();

    setTimeout(function () {
        stopSpeech();
    }, duration);
}

function sayText(text) {
    if (!text) return;

    console.log("Miss Minutes says:", text);

    const words = text.trim().split(/\s+/).length;

    let duration = words * 320;

    if (duration < 900) duration = 900;
    if (duration > 6000) duration = 6000;

    speakTest(duration);
}
