// ======================
// BLINK
// ======================

let blinkEnabled = true;
let blinkTimer = null;

function blink() {
    if (!window.characterState) return;

    characterState.blink.leftBlink = 1;
    characterState.blink.rightBlink = 1;
    characterState.blink.leftLash = 80;
    characterState.blink.rightLash = 80;

    setTimeout(function () {
        delete characterState.blink.leftBlink;
	delete characterState.blink.rightBlink;
        delete characterState.blink.leftLash;
	delete characterState.blink.rightLash;
    }, 90);
}
function scheduleBlink() {

    if (!blinkEnabled) return;

    const delay = 2000 + Math.random() * 4000;

    blinkTimer = setTimeout(function () {

        blink();
        scheduleBlink();

    }, delay);
}

function startBlinking() {

    stopBlinking();

    blinkEnabled = true;

    scheduleBlink();
}

function stopBlinking() {

    blinkEnabled = false;

    clearTimeout(blinkTimer);
}