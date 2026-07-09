function setHeadTurn(value) {
    if (!window.characterState) return;

    const turn = Math.max(-1, Math.min(1, value));
    const amount = Math.abs(turn);

    characterState.idle.headTurn = turn;
    characterState.idle.headSquash = 1 - amount * 0.12;
    characterState.idle.depthOffset = turn * -12;
    characterState.idle.featureOffset = turn * 4;

    // Arm nearest the turned side moves closer to clock face
    //characterState.idle.leftArmShift = turn < 0 ? 20 : 0;
    //characterState.idle.rightArmShift = turn > 0 ? -20 : 0;
    characterState.idle.leftArmShift  = turn * -20;
    characterState.idle.rightArmShift = turn * -20;
    renderCharacter();
}

window.setHeadTurn = setHeadTurn;
