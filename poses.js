// poses.js

const POSES = {
    neutral: {
        mouth: 0.2,
        mouthWidth: 28,
        mouthY: 25,

	leftEyeScaleY:1,
	rightEyeScaleY:1,

        leftPupilX: 0,
        leftPupilY: 0,
        rightPupilX: 0,
        rightPupilY: 0,

        leftBlink: 0,
        rightBlink: 0,

        leftUpper: 0,
        leftLower: 0,
        rightUpper: 0,
        rightLower: 0
    },

    happy: {
        mouth: 0.45,
        mouthWidth: 34,
        mouthY: 24,

	leftEyeScaleY:.88,
	rightEyeScaleY:.88,

        leftPupilX: 0,
        leftPupilY: -2,
        rightPupilX: 0,
        rightPupilY: -2,

        leftBlink: 0.12,
        rightBlink: 0.12,

        leftUpper: 8,
        leftLower: -8,
        rightUpper: -8,
        rightLower: 8
    },

    worried: {
        mouth: 0.15,
        mouthWidth: 22,
        mouthY: 27,

	leftEyeScaleY:1.15,
	rightEyeScaleY:1.15,

        leftPupilX: -2,
        leftPupilY: -3,
        rightPupilX: -2,
        rightPupilY: -3,

        leftBlink: 0.08,
        rightBlink: 0.08,

        leftUpper: -10,
        leftLower: 12,
        rightUpper: 10,
        rightLower: -12
    },

    angry: {
        mouth: 0.25,
        mouthWidth: 24,
        mouthY: 23,

        leftPupilX: 0,
        leftPupilY: 2,
        rightPupilX: 0,
        rightPupilY: 2,

        leftBlink: 0.22,
        rightBlink: 0.22,

        leftUpper: -25,
        leftLower: 15,
        rightUpper: 25,
        rightLower: -15
    },

    sad: {
        mouth: 0.12,
        mouthWidth: 22,
        mouthY: 28,

	leftEyeScaleY:.82,
	rightEyeScaleY:.82,

        leftPupilX: 0,
        leftPupilY: 4,
        rightPupilX: 0,
        rightPupilY: 4,

        leftBlink: 0.15,
        rightBlink: 0.15,


        leftUpper: -6,
        leftLower: 10,
        rightUpper: 6,
        rightLower: -10
    }
};

function setPose(name) {
    const pose = POSES[name];

    if (!pose || !window.characterState) return;

    characterState.base.mouth = pose.mouth;
    characterState.base.mouthWidth = pose.mouthWidth;
    characterState.base.mouthY = pose.mouthY;

    characterState.base.leftPupilX = pose.leftPupilX;
    characterState.base.leftPupilY = pose.leftPupilY;
    characterState.base.rightPupilX = pose.rightPupilX;
    characterState.base.rightPupilY = pose.rightPupilY;

    characterState.base.leftBlink = pose.leftBlink;
    characterState.base.rightBlink = pose.rightBlink;
    characterState.base.leftLash = pose.leftLash;
    characterState.base.rightLash = pose.rightLash;

    characterState.base.leftUpper = pose.leftUpper;
    characterState.base.leftLower = pose.leftLower;
    characterState.base.rightUpper = pose.rightUpper;
    characterState.base.rightLower = pose.rightLower;
}