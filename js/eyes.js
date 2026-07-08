/* ==========================
   EYES
========================== */

function lookCenter() {
    setEyes(0, 0);
}

function lookLeft() {
    setEyes(-6, 0);
}

function lookRight() {
    setEyes(6, 0);
}

function lookUp() {
    setEyes(0, -5);
}

function lookDown() {
    setEyes(0, 5);
}

function setEyes(x, y) {

    if (!window.characterState) return;

    characterState.idle.leftPupilX = x;
    characterState.idle.leftPupilY = y;

    characterState.idle.rightPupilX = x;
    characterState.idle.rightPupilY = y;
}
