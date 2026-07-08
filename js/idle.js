// idle.js

let idleTimer = null;
let idleEnabled = true;

function startIdle() {

    if (idleTimer) return;

    idleTimer = setInterval(doIdle, 3000);

}

function stopIdle() {

    clearInterval(idleTimer);
    idleTimer = null;

}

function doIdle() {

    if (!idleEnabled) return;

    const r = Math.random();

    if (r < .20) {

        lookLeft();

    } else if (r < .40) {

        lookRight();

    } else if (r < .55) {

        lookUp();

    } else if (r < .70) {

        lookDown();

    } else {

        lookCenter();

    }

}
