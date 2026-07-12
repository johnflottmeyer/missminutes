// speech.js
window.speechSynthesis.onvoiceschanged = function () {
    console.log(
        "Available voices:",
        window.speechSynthesis.getVoices().map(function (voice) {
            return voice.name + " — " + voice.lang;
        })
    );
};
function findMissMinutesStyleVoice() {

    const voices = window.speechSynthesis.getVoices();

    const preferredNames = [
        "Microsoft Aria Online",
        "Microsoft Jenny Online",
        "Microsoft Zira",
        "Google US English",
        "Samantha"
    ];

    for (const name of preferredNames) {
        const match = voices.find(function (voice) {
            return voice.name.includes(name);
        });

        if (match) {
            return match;
        }
    }

    // Fall back to an English female-sounding voice when available.
    return voices.find(function (voice) {
        const name = voice.name.toLowerCase();

        return voice.lang.startsWith("en") &&
            (
                name.includes("female") ||
                name.includes("aria") ||
                name.includes("jenny") ||
                name.includes("zira") ||
                name.includes("samantha")
            );
    }) || voices.find(function (voice) {
        return voice.lang.startsWith("en");
    });
}

let speechTimer = null;
let syllableTimer = null;
let isSpeaking = false;
let currentUtterance = null;


/* =========================================
   MOUTH STATE
========================================= */

function setMouthSpeech(amount) {

    if (!window.characterState) return;

    window.characterState.speech.mouthSpeech = amount;

    renderCharacter();
}


/* =========================================
   APPROXIMATE MOUTH SHAPES

   These values control how far the mouth opens.
   Later, these can also control mouth width and
   mouth shape for better phoneme animation.
========================================= */

function getSoundShape(letter) {
    letter = letter.toLowerCase();

    const shapes = {
        // Wide/open vowel sounds
        a: 0.48,
        e: 0.28,
        i: 0.22,
        o: 0.52,
        u: 0.42,
        y: 0.24,

        // Closed-lip consonants
        m: 0.02,
        b: 0.04,
        p: 0.02,

        // Teeth/lip sounds
        f: 0.12,
        v: 0.14,

        // Tongue consonants
        l: 0.20,
        n: 0.14,
        r: 0.22,
        s: 0.10,
        t: 0.10,
        d: 0.14,
        z: 0.12,

        // Stronger consonants
        c: 0.18,
        g: 0.22,
        j: 0.26,
        k: 0.18,
        q: 0.18,
        w: 0.28,
        x: 0.18,

        // Breath sounds
        h: 0.18
    };

    return shapes[letter] ?? 0.12;
}


/* =========================================
   WORD/SYLLABLE ANIMATION
========================================= */

function animateWord(word) {
    clearInterval(syllableTimer);
    syllableTimer = null;

    const sounds = createSoundSequence(word);

    if (!sounds.length) {
        setMouthSpeech(0);
        return;
    }

    let soundIndex = 0;

    function showNextSound() {
        if (!isSpeaking) return;

        const sound = sounds[soundIndex];
        setMouthSpeech(sound.amount);

        soundIndex++;

        if (soundIndex >= sounds.length) {
            clearInterval(syllableTimer);
            syllableTimer = null;

            // Briefly relax the mouth after the word.
            setTimeout(function () {
                if (isSpeaking) {
                    setMouthSpeech(0.04);
                }
            }, 55);
        }
    }

    showNextSound();

    syllableTimer = setInterval(showNextSound, 105);
}


function createSoundSequence(word) {
    const cleanedWord = word
        .toLowerCase()
        .replace(/[^a-z']/g, "");

    if (!cleanedWord) return [];

    const sounds = [];

    for (let i = 0; i < cleanedWord.length; i++) {
        const letter = cleanedWord[i];
        const nextLetter = cleanedWord[i + 1] || "";
        const pair = letter + nextLetter;

        /*
         * Common joined sounds are treated as one mouth movement.
         */
        if (
            pair === "th" ||
            pair === "sh" ||
            pair === "ch" ||
            pair === "ph" ||
            pair === "wh" ||
            pair === "ck"
        ) {
            sounds.push({
                letters: pair,
                amount: getPairShape(pair)
            });

            i++;
            continue;
        }

        /*
         * Combine consecutive vowels so words such as
         * "rain", "look", and "voice" do not flutter
         * between too many shapes.
         */
        if (isVowel(letter) && isVowel(nextLetter)) {
            sounds.push({
                letters: pair,
                amount: Math.max(
                    getSoundShape(letter),
                    getSoundShape(nextLetter)
                )
            });

            i++;
            continue;
        }

        sounds.push({
            letters: letter,
            amount: getSoundShape(letter)
        });
    }

    return simplifySoundSequence(sounds);
}


function getPairShape(pair) {
    const pairShapes = {
        th: 0.16,
        sh: 0.18,
        ch: 0.24,
        ph: 0.12,
        wh: 0.30,
        ck: 0.16
    };

    return pairShapes[pair] ?? 0.16;
}


function isVowel(letter) {
    return "aeiouy".includes(letter);
}


/*
 * Removes nearly identical consecutive positions.
 * This keeps the mouth from vibrating unnecessarily.
 */
function simplifySoundSequence(sounds) {
    const simplified = [];

    sounds.forEach(function (sound) {
        const previous = simplified[simplified.length - 1];

        if (
            previous &&
            Math.abs(previous.amount - sound.amount) < 0.06
        ) {
            return;
        }

        simplified.push(sound);
    });

    return simplified;
}


/* =========================================
   FALLBACK SPEECH ANIMATION

   Used if the browser does not provide useful
   word boundary events.
========================================= */

function startFallbackSpeechAnimation() {
    clearInterval(speechTimer);

    let previousAmount = 0.08;

    speechTimer = setInterval(function () {
        if (!isSpeaking) return;

        const shapes = [
            0.04,
            0.10,
            0.18,
            0.28,
            0.42,
            0.52
        ];

        let amount =
            shapes[Math.floor(Math.random() * shapes.length)];

        /*
         * Prevent very large jumps between frames.
         */
        if (Math.abs(amount - previousAmount) > 0.30) {
            amount = (amount + previousAmount) / 2;
        }

        previousAmount = amount;
        setMouthSpeech(amount);
    }, 95);
}


/* =========================================
   SPEECH CONTROL
========================================= */

function startSpeech() {
    if (isSpeaking) return;

    stopIdle();

    isSpeaking = true;

    headCenter();
    lookCenter();

    setMouthSpeech(0.08);
}


function stopSpeech() {
    isSpeaking = false;

    clearInterval(speechTimer);
    clearInterval(syllableTimer);

    speechTimer = null;
    syllableTimer = null;
    currentUtterance = null;

    setMouthSpeech(0);

    startIdle();
}


/* =========================================
   SPEAK TEXT
========================================= */

function sayText(text) {
    if (!text || !text.trim()) return;

    window.speechSynthesis.cancel();

    console.log("Miss Minutes says:", text);

    const utterance = new SpeechSynthesisUtterance(text);

    currentUtterance = utterance;

    const voice = findMissMinutesStyleVoice();

	if (voice) {
    	utterance.voice = voice;
    	utterance.lang = voice.lang;
	}

	utterance.rate = 1.15;
	utterance.pitch = 1.45;
	utterance.volume = 1;

    let receivedBoundary = false;

    utterance.onstart = function () {
        startSpeech();

        /*
         * Start the fallback immediately. If boundary events
         * arrive, animateWord() will replace its movement.
         */
        startFallbackSpeechAnimation();
    };

    utterance.onboundary = function (event) {
        if (!isSpeaking) return;

        receivedBoundary = true;

        /*
         * Stop random fallback movement once the browser gives
         * us actual word timing.
         */
        clearInterval(speechTimer);
        speechTimer = null;

        const word = getWordAtIndex(text, event.charIndex);

        if (word) {
            animateWord(word);
        }
    };

    utterance.onend = function () {
        stopSpeech();
    };

    utterance.onerror = function (event) {
        console.error("Speech error:", event.error);
        stopSpeech();
    };

    window.speechSynthesis.speak(utterance);
}


/* =========================================
   FIND THE WORD AT A CHARACTER POSITION
========================================= */

function getWordAtIndex(text, charIndex) {
    let start = charIndex;
    let end = charIndex;

    /*
     * Some browsers give the space before the word.
     */
    while (
        start < text.length &&
        /\s/.test(text[start])
    ) {
        start++;
    }

    end = start;

    while (
        end < text.length &&
        /[a-zA-Z']/i.test(text[end])
    ) {
        end++;
    }

    return text.slice(start, end);
}


/* =========================================
   MANUAL TEST
========================================= */

function speakTest(duration) {
    duration = duration || 3000;

    startSpeech();
    startFallbackSpeechAnimation();

    setTimeout(function () {
        stopSpeech();
    }, duration);
}
