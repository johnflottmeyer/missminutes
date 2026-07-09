// ======================
// BLINK
// ======================

let blinkEnabled = true;
let blinkTimer = null;

function blink() {
    if (!window.characterState) return;

    // Close blink
    characterState.blink.leftBlink = 1;
    characterState.blink.rightBlink = 1;

    characterState.blink.leftLash = 80;
    characterState.blink.rightLash = 80;

    // Temporarily straighten angled lids during blink
    characterState.blink.leftLidRotate = 0;
    characterState.blink.rightLidRotate = 0;

    characterState.blink.lashOpacity = 0;

    renderCharacter();

    setTimeout(function () {
        // Remove blink overrides so pose values return
        delete characterState.blink.leftBlink;
        delete characterState.blink.rightBlink;

        delete characterState.blink.leftLash;
        delete characterState.blink.rightLash;

        delete characterState.blink.leftLidRotate;
        delete characterState.blink.rightLidRotate;

        delete characterState.blink.lashOpacity;

        renderCharacter();
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
