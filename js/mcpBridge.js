// ==========================
// AIPI MCP TEXT BRIDGE
// ==========================

(function () {
  const MCP_TEXT_URL = "http://127.0.0.1:8000/latest-text";

  const POLL_INTERVAL = 250;

  let lastMessageId = 0;

  async function checkForAipiText() {
    try {
      const response = await fetch(`${MCP_TEXT_URL}?t=${Date.now()}`, {
        cache: "no-store",
      });

      if (!response.ok) {
        return;
      }

      const data = await response.json();

      if (!data) {
        return;
      }

      if (!data.id || !data.text) {
        return;
      }

      if (data.id === lastMessageId) {
        return;
      }

      lastMessageId = data.id;

      console.log("AIPI → Miss Minutes:", data.text);

      // This event lets speech.js receive the
      // AIPI text without coupling the MCP code
      // directly to the speech engine.

      window.dispatchEvent(
        new CustomEvent("aipiTextReceived", {
          detail: {
            id: data.id,
            text: data.text,
          },
        }),
      );
    } catch (error) {
      // Don't flood the console if MCP is
      // temporarily offline.
    }
  }

  function startAipiBridge() {
    console.log("AIPI MCP text bridge started");

    checkForAipiText();

    setInterval(checkForAipiText, POLL_INTERVAL);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", startAipiBridge);
  } else {
    startAipiBridge();
  }
})();
