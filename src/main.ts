// src/main.ts
import { log } from "./utils/logger";
import { getLatestHypothesisByStatus, HypothesisStatus } from "./db/hypothesis";
import { validateHypothesis } from "./utils/validateHypothesis";

(async () => {
  log("Starting Geo-Voyager...");
  const hypothesis = await getLatestHypothesisByStatus(
    HypothesisStatus.PENDING
  );
  if (!hypothesis) {
    log("No hypothesis to validate.");
    return;
  }
  const hypothesisId = hypothesis.id;
  const result = await validateHypothesis(hypothesisId);
  console.log(`Hypothesis ID ${hypothesisId} validation result: ${result}`);
})();
