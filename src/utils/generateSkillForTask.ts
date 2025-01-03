import { promises as fs } from "fs";
import path from "path";
import { ChatOllama } from "@langchain/ollama";
import { saveSkillToDatabase } from "../db/skill";

/**
 * タスクに対応するスキルを生成
 * @param taskDescription タスクの説明
 * @param referenceSkills 参考スキル（存在する場合）
 * @returns 成功したかどうか
 */
export const generateSkillForTask = async (
  taskDescription: string,
  referenceSkills: string[]
): Promise<boolean> => {
  let attempts = 0;
  const maxAttempts = 5;
  let lastError = null;

  const qwenModel = new ChatOllama({
    model: "qwen2.5:7b",
    temperature: 0,
  });

  while (attempts < maxAttempts) {
    attempts++;
    console.log(
      `🛠️ Generating skill for task: "${taskDescription}" (Attempt ${attempts})`
    );

    // プロンプトを生成
    const prompt = `
      Task: ${taskDescription}

      Using the following existing skills as reference:
      ${referenceSkills.join("\n")}

      Create a new skill in TypeScript that performs the task described above.
      Make sure it is reusable and follows best practices. Include comments for clarity.

      ${
        lastError
          ? `Fix the following error from the last attempt: ${lastError}`
          : ""
      }
    `;

    // スキルを生成
    const res = await qwenModel.invoke(prompt);
    const skillCode = res.content as string;

    // 一時ファイルにスキルを保存
    const tempFilePath = path.join(
      __dirname,
      `../../tmp/generated_skill_${Date.now()}.ts`
    );
    await fs.writeFile(tempFilePath, skillCode);

    try {
      // スキルをインポートして実行テスト
      const skillModule = await import(`file://${path.resolve(tempFilePath)}`);
      const result = await skillModule.default();
      console.log(`✅ Skill executed successfully with result: ${result}`);

      // スキルをデータベースに保存
      await saveSkillToDatabase(taskDescription, skillCode);
      console.log(`💾 Skill saved to database for task: ${taskDescription}`);
      return true; // 成功
    } catch (error) {
      console.error(`❌ Skill execution failed: ${error.message}`);
      lastError = error.message;
    }
  }

  console.error(
    "⚠️ Failed to generate a working skill after multiple attempts."
  );
  return false;
};
