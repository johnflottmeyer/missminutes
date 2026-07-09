let standbyEnabled = false;

function enterStandby() {
    const character = document.getElementById("character");
    if (!character) return;

    standbyEnabled = true;

    stopIdle();
    stopBlinking();

    character.classList.remove("standby-on");
    character.classList.add("standby-off");
}

function exitStandby() {
    const character = document.getElementById("character");
    if (!character) return;

    standbyEnabled = false;

    character.classList.remove("standby-off");
    character.classList.add("standby-on");

    setTimeout(function () {
        character.classList.remove("standby-on");
        startIdle();
        startBlinking();
    }, 650);
}

function toggleStandby() {
    if (standbyEnabled) {
        exitStandby();
    } else {
        enterStandby();
    }
}

window.enterStandby = enterStandby;
window.exitStandby = exitStandby;
window.toggleStandby = toggleStandby;

function isStandby() {
    return standbyEnabled;
}

window.isStandby = isStandby;
