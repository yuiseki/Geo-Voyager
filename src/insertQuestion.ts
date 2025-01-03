import { createQuestion } from "./db/question";

(async () => {
  console.log("🗺️  Initializing Geo-Voyager...");

  const args = process.argv.slice(2);
  if (args.length === 0) {
    console.log("⚠️  No NEW questions found.");
    return;
  }
  if (args.length > 1) {
    console.log("⚠️  Too many arguments.");
    return;
  }
  if (args.length === 1) {
    const question = args[0];
    console.log(`❓️ Insert new question: ${question}`);
    await createQuestion(question);
    console.log("✅  New question has been inserted.");
  }

  console.log("🗺️  Geo-Voyager has finished his journey.");
})();
