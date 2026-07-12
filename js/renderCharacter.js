/* ==========================
   RENDERER
========================== */

(function () {

    const cssMap = {
        mouth: ["--mouth-base", ""],
        mouthWidth: ["--mouth-width", "%"],
	mouthSpeech: ["--mouth-speech", ""],
        mouthY: ["--mouth-y", "%"],

        leftPupilX: ["--left-pupil-x", "%"],
        leftPupilY: ["--left-pupil-y", "%"],
        rightPupilX: ["--right-pupil-x", "%"],
        rightPupilY: ["--right-pupil-y", "%"],

        leftBlink: ["--left-blink", ""],
        rightBlink: ["--right-blink", ""],

        leftEyeScaleY: ["--left-eye-scale-y", ""],
        rightEyeScaleY: ["--right-eye-scale-y", ""],

        leftLidRotate: ["--left-lid-rotate", "deg"],
        rightLidRotate: ["--right-lid-rotate", "deg"],

        leftLash: ["--left-lash", ""],
        rightLash: ["--right-lash", ""],
        lashOpacity: ["--lash-opacity", ""],

        leftUpper: ["--left-upper", "deg"],
        leftLower: ["--left-lower", "deg"],
        rightUpper: ["--right-upper", "deg"],
        rightLower: ["--right-lower", "deg"],

	headTurn: ["--head-turn", ""],
	headSquash: ["--head-squash", ""],
	depthOffset: ["--depth-offset", "%"],
	featureOffset: ["--feature-offset", "%"],

	leftArmShift: ["--left-arm-shift", "%"],
	rightArmShift: ["--right-arm-shift", "%"],
    };

    function renderCharacter() {

        const character = document.getElementById("character");

        if (!character || !window.characterState) return;

        const state = {
            ...characterState.base,
            ...characterState.idle,
            ...characterState.speech,
            ...characterState.gesture,
            ...characterState.blink
        };
	

        Object.entries(cssMap).forEach(([key, [cssVar, unit]]) => {
            if (state[key] !== undefined) {
                character.style.setProperty(cssVar, state[key] + unit);
            }
        });

	const mouth = document.getElementById("mouth");

	if (mouth) {
    		mouth.classList.remove(
        		"mouth-smile",
        		"mouth-frown",
        		"mouth-o",
        		"mouth-flat",
        		"mouth-smirk"
    		);

    		const shape = state.mouthShape || "smile";

    		mouth.classList.add("mouth-" + shape);
	}
    }

    window.renderCharacter = renderCharacter;

})();
