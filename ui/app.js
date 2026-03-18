const form = document.getElementById("joke-form");
const input = document.getElementById("joke-input");
const submitBtn = document.getElementById("submit-btn");
const results = document.getElementById("results");
const judgeSection = document.getElementById("judge-section");
const judgeOutput = document.getElementById("judge-output");
const rewriterSection = document.getElementById("rewriter-section");
const rewriterOutput = document.getElementById("rewriter-output");
const errorMsg = document.getElementById("error-msg");

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const joke = input.value.trim();
  if (!joke) return;

  // Reset UI
  results.classList.remove("hidden");
  judgeSection.classList.remove("hidden", "funny", "not-funny");
  rewriterSection.classList.add("hidden");
  errorMsg.classList.add("hidden");
  judgeOutput.innerHTML = '<span class="spinner"></span> Judging your joke...';
  submitBtn.disabled = true;

  try {
    const response = await fetch("/invocations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        input: [{ role: "user", content: joke }],
        stream: true,
      }),
    });

    if (!response.ok) {
      throw new Error(`Server returned ${response.status}`);
    }

    // The streaming endpoint returns newline-delimited JSON chunks
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let chunkIndex = 0;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // Process complete lines (each line is a JSON object)
      const lines = buffer.split("\n");
      buffer = lines.pop(); // Keep incomplete line in buffer

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) continue;

        // Handle SSE "data:" prefix if present
        const jsonStr = trimmed.startsWith("data:") ? trimmed.slice(5).trim() : trimmed;
        if (!jsonStr || jsonStr === "[DONE]") continue;

        try {
          const data = JSON.parse(jsonStr);
          const text = extractText(data);
          if (!text) continue;

          if (chunkIndex === 0) {
            // First chunk is always from the judge
            judgeOutput.textContent = text;
            const isFunny = text.toLowerCase().startsWith("funny!");
            judgeSection.classList.add(isFunny ? "funny" : "not-funny");
          } else {
            // Subsequent chunks are from the rewriter
            rewriterSection.classList.remove("hidden");
            rewriterOutput.textContent = text;
          }
          chunkIndex++;
        } catch {
          // Skip non-JSON lines
        }
      }
    }

    // If we never got a streamed chunk, try parsing the full response as JSON
    if (chunkIndex === 0 && buffer.trim()) {
      try {
        const data = JSON.parse(buffer.trim());
        const text = extractText(data);
        if (text) {
          judgeOutput.textContent = text;
          const isFunny = text.toLowerCase().startsWith("funny!");
          judgeSection.classList.add(isFunny ? "funny" : "not-funny");
        }
      } catch {
        // ignore
      }
    }
  } catch (err) {
    errorMsg.textContent = `Error: ${err.message}`;
    errorMsg.classList.remove("hidden");
    judgeSection.classList.add("hidden");
  } finally {
    submitBtn.disabled = false;
  }
});

/**
 * Extract text from a Responses API message.
 * Handles both { output: [{ content: [{ text }] }] }
 * and flat { text } shapes.
 */
function extractText(data) {
  // Standard Responses API shape
  if (data.output) {
    for (const item of data.output) {
      if (item.content) {
        for (const block of item.content) {
          if (block.text) return block.text;
        }
      }
    }
  }
  // Fallback
  if (data.text) return data.text;
  return null;
}
