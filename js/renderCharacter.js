/* ==========================
   RENDERER
========================== */

(function () {

    const cssMap = {
        mouth: ["--mouth-base", ""],
    	mouthWidth: ["--mouth-width", "%"],
    	mouthY: ["--mouth-y", "%"],

    	leftPupilX: ["--left-pupil-x", "%"],
    	leftPupilY: ["--left-pupil-y", "%"],
    	rightPupilX: ["--right-pupil-x", "%"],
    	rightPupilY: ["--right-pupil-y", "%"],

    	leftBlink: ["--left-blink", ""],
    	rightBlink: ["--right-blink", ""],


    	leftUpper: ["--left-upper", "deg"],
    	leftLower: ["--left-lower", "deg"],
    	rightUpper: ["--right-upper", "deg"],
    	rightLower: ["--right-lower", "deg"]
    };

    function renderCharacter() {

        const character = document.getElementById("character");

        if (!character || !window.characterState) return;

        const state = {
            ...characterState.base,
            ...characterState.idle,
            ...characterState.blink,
            ...characterState.speech,
            ...characterState.gesture
        };

        Object.entries(cssMap).forEach(([key, [cssVar, unit]]) => {
            if (state[key] !== undefined) {
                character.style.setProperty(cssVar, state[key] + unit);
            }
        });
    }

    window.renderCharacter = renderCharacter;

})();
