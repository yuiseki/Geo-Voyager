import { promises as fs } from "fs";
import path from "path";
import { ChatOllama, OllamaEmbeddings } from "@langchain/ollama";
import { getAllSkills, saveSkillToDatabase } from "../db/skill";
import { SemanticSimilarityExampleSelector } from "@langchain/core/example_selectors";
import { FewShotPromptTemplate, PromptTemplate } from "@langchain/core/prompts";
import { MemoryVectorStore } from "langchain/vectorstores/memory";
import { RunnableSequence } from "@langchain/core/runnables";

/**
 * タスクに対応するスキルを生成
 * @param taskDescription タスクの説明
 * @param referenceSkills 参考スキル（存在する場合）
 * @returns 成功したかどうか
 */
export const generateSkillForTask = async (
  taskDescription: string
): Promise<boolean> => {
  let attempts = 0;
  const maxAttempts = 20;
  let lastError = null;
  let lastCode = null;

  const model = new ChatOllama({
    model: "qwen2.5:14b",
    temperature: 0,
  });
  const embeddings = new OllamaEmbeddings({
    model: "snowflake-arctic-embed:22m",
  });
  const vectorStore = new MemoryVectorStore(embeddings);

  while (attempts < maxAttempts) {
    attempts++;
    console.log(
      `🛠️  Generating skill for task: "${taskDescription}" (Attempt ${attempts})`
    );

    // プロンプトを生成
    const exampleSelector = new SemanticSimilarityExampleSelector({
      vectorStore: vectorStore,
      k: 4,
      inputKeys: ["input"],
    });
    const examplePrompt = PromptTemplate.fromTemplate(
      `\`\`\`typescript\n{output}\`\`\``
    );

    const currentAllSkills = await getAllSkills();
    for (const example of currentAllSkills) {
      await exampleSelector.addExample({
        input: example.description,
        output: example.code.replaceAll("{", "{{").replaceAll("}", "}}"),
      });
    }

    const dynamicPrompt = new FewShotPromptTemplate({
      exampleSelector: exampleSelector,
      examplePrompt: examplePrompt,
      prefix: "Using the following existing skills as reference:",
      suffix: `Task: {input}

Create a new skill in TypeScript that performs the task described above.

Ensure the code must be surrounded by three backtick to indicate that it is a code block.

Ensure the first line of the script includes a description in the following format:
// description: {input}

Ensure the second line of the script includes the file_path in the following format:
// file_path: src/lib/skills/path/to/your/file.ts

Make sure the code is reusable and follows best practices. Include comments in English for clarity.

${
  lastCode
    ? `Your previous code of last attempt: \n\`\`\`typescript\n${lastCode}\n\`\`\``
    : ""
}
${
  lastError
    ? `Fix the following error from the last attempt:\n${lastError}`
    : ""
}`,
      inputVariables: ["input"],
    });
    const chain = RunnableSequence.from([dynamicPrompt, model]);

    // スキルを生成
    const res = await chain.invoke({ input: taskDescription });
    const content = res.content as string;
    // ...\n```typescript\n{code}\n```\.... となっている
    const skillCode = content.match(/```typescript\n([\s\S]+)\n```/)?.[1];
    if (!skillCode) {
      console.error("❌ Failed to generate a skill code: no code found.");
      continue;
    }

    console.log(`🧠 Generated skill code:\n${skillCode}`);

    // 一時ファイルにスキルを保存
    const tempFilePath = path.join(
      __dirname,
      `../../tmp/skills/generated_skill_${Date.now()}.ts`
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
      if (error instanceof Error) {
        console.error(`❌ Skill execution failed:`);
        const replaceErrors = (_key: any, value: any) => {
          if (value instanceof Error) {
            const error: any = {};
            Object.getOwnPropertyNames(value).forEach((name) => {
              error[name] = (value as any)[name];
            });
            return error;
          }

          return value;
        };
        console.error(JSON.stringify(error, replaceErrors, 2));
        lastError = JSON.stringify(error, replaceErrors, 2)
          .replaceAll("{", "{{")
          .replaceAll("}", "}}");
        lastCode = skillCode.replaceAll("{", "{{").replaceAll("}", "}}");
      }
    }
  }

  console.error(
    "⚠️ Failed to generate a working skill after multiple attempts."
  );
  return false;
};
