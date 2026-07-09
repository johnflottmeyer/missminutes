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

function headLeft() {
    setHeadTurn(-0.45);
console.log("turnleft");
}

function headCenter() {
    setHeadTurn(0);
console.log("turncenter");
}

function headRight() {
    setHeadTurn(0.45);
console.log("turnright");
}

function doIdle() {

    if (!idleEnabled) return;

    const r = Math.random();

    if (r < .15) {

        lookLeft();
        headLeft();

    } else if (r < .30) {

        lookRight();
        headRight();

    } else if (r < .45) {

        lookUp();
        headCenter();

    } else if (r < .60) {

        lookDown();
        headCenter();

    } else if (r < .80) {

        lookCenter();
        headCenter();

    } else {

        // Eyes stay centered but the head slowly glances
        if (Math.random() < .5)
            headLeft();
        else
            headRight();
    }

}
