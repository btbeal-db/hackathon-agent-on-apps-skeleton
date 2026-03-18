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
      }),
    });

    if (!response.ok) {
      const body = await response.text();
      throw new Error(`Server returned ${response.status}: ${body}`);
    }

    const data = await response.json();

    // Extract text from each output item (one per graph node)
    const texts = [];
    if (data.output) {
      for (const item of data.output) {
        if (item.content) {
          for (const block of item.content) {
            if (block.text) texts.push(block.text);
          }
        }
      }
    }

    if (texts.length === 0) {
      throw new Error("No response from agent");
    }

    // First text is always from the judge
    judgeOutput.textContent = texts[0];
    const isFunny = texts[0].toLowerCase().startsWith("funny!");
    judgeSection.classList.add(isFunny ? "funny" : "not-funny");

    // Second text (if present) is from the rewriter
    if (texts.length > 1) {
      rewriterSection.classList.remove("hidden");
      rewriterOutput.textContent = texts[1];
    }
  } catch (err) {
    errorMsg.textContent = `Error: ${err.message}`;
    errorMsg.classList.remove("hidden");
    judgeSection.classList.add("hidden");
  } finally {
    submitBtn.disabled = false;
  }
});
