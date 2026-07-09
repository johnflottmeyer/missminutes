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

    button.textContent =
        isStandby() ? "Wake Up" : "Standby";

});
