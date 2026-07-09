// poses.js

const POSES = {
    neutral: {
         mouth: 0.2,
         mouthWidth: 28,
         mouthY: 25,
         mouthShape: "smile",

        leftEyeScaleY: 1,
        rightEyeScaleY: 1,

        leftLidRotate: 0,
        rightLidRotate: 0,

        leftPupilX: 0,
        leftPupilY: 0,
        rightPupilX: 0,
        rightPupilY: 0,

        leftBlink: 0,
        rightBlink: 0,

        leftLash: 0,
        rightLash: 0,
        lashOpacity: 1,

        leftUpper: 0,
        leftLower: 0,
        rightUpper: 0,
        rightLower: 0
    },

    happy: {
        mouth: 0.45,
        mouthWidth: 34,
        mouthY: 24,
        mouthShape: "smile",

        leftEyeScaleY: 0.88,
        rightEyeScaleY: 0.88,

        leftLidRotate: -8,
        rightLidRotate: 8,

        leftPupilX: 0,
        leftPupilY: -2,
        rightPupilX: 0,
        rightPupilY: -2,

        leftBlink: 0.12,
        rightBlink: 0.12,

        leftLash: 0,
        rightLash: 0,
        lashOpacity: 1,

        leftUpper: 8,
        leftLower: -8,
        rightUpper: -8,
        rightLower: 8
    },

    worried: {
        mouth: 0.55,
        mouthWidth: 18,
        mouthY: 26,
        mouthShape: "frown",

        leftEyeScaleY: 1.15,
        rightEyeScaleY: 1.15,

        leftLidRotate: -10,
        rightLidRotate: 10,

        leftPupilX: -2,
        leftPupilY: -3,
        rightPupilX: -2,
        rightPupilY: -3,

        leftBlink: 0.08,
        rightBlink: 0.08,

        leftLash: 0,
        rightLash: 0,
        lashOpacity: 1,

        leftUpper: -10,
        leftLower: 12,
        rightUpper: 10,
        rightLower: -12
    },

    angry: {
         mouth: 0.12,
         mouthWidth: 24,
         mouthY: 28,
         mouthShape: "frown",

        leftEyeScaleY: 0.8,
        rightEyeScaleY: 0.8,

        leftLidRotate: 12,
        rightLidRotate: -12,

        leftPupilX: 0,
        leftPupilY: 2,
        rightPupilX: 0,
        rightPupilY: 2,

        leftBlink: 0.22,
        rightBlink: 0.22,

        leftLash: 0,
        rightLash: 0,
        lashOpacity: 1,

        leftUpper: 25,
        leftLower: -85,
        rightUpper: -25,
        rightLower: 85,
    },

    sad: {
        mouth: 0.35,
        mouthWidth: 18,
        mouthY: 26,
        mouthShape: "frown",

        leftEyeScaleY: 0.7,
        rightEyeScaleY: 0.7,

        leftLidRotate: -8,
        rightLidRotate: 8,

        leftPupilX: 0,
        leftPupilY: 4,
        rightPupilX: 0,
        rightPupilY: 4,

        leftBlink: 0.15,
        rightBlink: 0.15,

        leftLash: 0,
        rightLash: 0,
        lashOpacity: 1,

        leftUpper: -6,
        leftLower: 10,
        rightUpper: 6,
        rightLower: -10
    },

suprised: {
        mouth: 0.55,
        mouthWidth: 18,
        mouthY: 26,
        mouthShape: "o",

        leftEyeScaleY: 1.15,
        rightEyeScaleY: 1.15,

        leftLidRotate: 0,
        rightLidRotate: 0,

        leftPupilX: 0,
        leftPupilY: 4,
        rightPupilX: 0,
        rightPupilY: 4,

        leftBlink: 0,
        rightBlink: 0,

        leftLash: 0,
        rightLash: 0,
        lashOpacity: 1,

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
    characterState.base.mouthShape = pose.mouthShape;

    characterState.base.leftEyeScaleY = pose.leftEyeScaleY;
    characterState.base.rightEyeScaleY = pose.rightEyeScaleY;

    characterState.base.leftLidRotate = pose.leftLidRotate;
    characterState.base.rightLidRotate = pose.rightLidRotate;

    characterState.base.leftPupilX = pose.leftPupilX;
    characterState.base.leftPupilY = pose.leftPupilY;
    characterState.base.rightPupilX = pose.rightPupilX;
    characterState.base.rightPupilY = pose.rightPupilY;

    characterState.base.leftBlink = pose.leftBlink;
    characterState.base.rightBlink = pose.rightBlink;

    characterState.base.leftLash = pose.leftLash;
    characterState.base.rightLash = pose.rightLash;
    characterState.base.lashOpacity = pose.lashOpacity;

    characterState.base.leftUpper = pose.leftUpper;
    characterState.base.leftLower = pose.leftLower;
    characterState.base.rightUpper = pose.rightUpper;
    characterState.base.rightLower = pose.rightLower;

    renderCharacter();
}
