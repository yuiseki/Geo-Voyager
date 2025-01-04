import { promises as fs } from "fs";
import path from "path";
import { ChatOllama, OllamaEmbeddings } from "@langchain/ollama";
import { getAllSkills, saveSkillToDatabase } from "../db/skill";
import { SemanticSimilarityExampleSelector } from "@langchain/core/example_selectors";
import { FewShotPromptTemplate, PromptTemplate } from "@langchain/core/prompts";
import { MemoryVectorStore } from "langchain/vectorstores/memory";
import { RunnableSequence } from "@langchain/core/runnables";
import { Skill } from "@prisma/client";

/**
 * タスクに対応するスキルを生成
 * @param taskDescription タスクの説明
 * @param referenceSkills 参考スキル（存在する場合）
 * @returns 成功したかどうか
 */
export const generateNewSkillForTask = async (
  taskDescription: string
): Promise<Skill> => {
  let attempts = 0;
  const maxAttempts = 20;
  let lastError = null;
  let lastCode = null;
  let lastHint = null;

  // 120秒待ってからやる
  const sleep = (msec: number) =>
    new Promise((resolve) => setTimeout(resolve, msec));
  // await sleep(120000);

  const model = new ChatOllama({
    model: "qwen2.5-coder:14b",
    temperature: 0,
    numCtx: 4096,
  });
  const embeddings = new OllamaEmbeddings({
    // model: "snowflake-arctic-embed:33m",
    model: "snowflake-arctic-embed:110m",
  });
  const vectorStore = new MemoryVectorStore(embeddings);

  while (attempts < maxAttempts) {
    attempts++;
    console.log(
      `🤖 Generating new skill for task: "${taskDescription}" (Attempt ${attempts})`
    );

    // プロンプトを生成
    const exampleSelector = new SemanticSimilarityExampleSelector({
      vectorStore: vectorStore,
      k: 3,
      inputKeys: ["input"],
    });
    const examplePrompt = PromptTemplate.fromTemplate(
      `\`\`\`typescript\n{output}\`\`\`\n`
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
      prefix: `Create a new skill by written TypeScript code that performs the task described below.
Using the following existing and working codes as reference:`,
      suffix: `Task: {input}

Ensure the code must be surrounded by three backtick to indicate that it is a code block.

Ensure the first line of the script includes a description in the following format:
// description: {input}

Ensure the second line of the script includes the file_path in the following format:
// file_path: src/lib/skills/path/to/your/file.ts

Make sure the code you replay must be executable and follows best practices.
The code shown as reference is working fine.
When possible, only partially modify the code shown as a reference.

Do not forget to import necessary libraries.
Include comments in English for clarity.

${
  taskDescription.includes("東京都") &&
  `
大田区は英語でOtaです。
世田谷区は英語でSetagayaです。
台東区は英語でTaitoです。
豊島区は英語でToshimaです。
品川区は英語でShinagawaです。`
}

${
  lastCode
    ? `Your previous code of last attempt: \n\`\`\`typescript\n${lastCode}\n\`\`\`\n`
    : ""
}
${
  lastError
    ? `Fix the following error from the last attempt code:\n${lastError}\n`
    : ""
}
${lastHint ? `Hint to fix the code: ${lastHint}` : ""}
`,
      inputVariables: ["input"],
    });
    const chain = RunnableSequence.from([dynamicPrompt, model]);

    // スキルを生成
    const res = await chain.invoke({ input: taskDescription });
    const content = res.content as string;
    // ...\n```typescript\n{code}\n```\n.... となっている
    const skillCode = content.match(/```typescript\n([\s\S]+)\n```/)?.[1];
    if (!skillCode) {
      console.error("❌ Failed to generate new skill: no code found.");
      continue;
    }

    // console.log(`🤖 Generated new skill code:`);
    // console.log(skillCode)

    // 動作確認のために、一時ファイルにスキルを保存
    const tempFilePath = path.join(
      __dirname,
      `../../tmp/skills/generated_skill_${Date.now()}.ts`
    );
    await fs.writeFile(tempFilePath, skillCode);

    try {
      // 一時ファイルからスキルをインポートして動作確認
      const skillModule = await import(`file://${path.resolve(tempFilePath)}`);
      const saveFilePath = skillCode.match(/file_path: (.+)/)?.[1];
      if (!saveFilePath) {
        console.error("❌ Something went wrong: no file_path found.");
        lastCode = skillCode.replaceAll("{", "{{").replaceAll("}", "}}");
        lastError = "No file_path found in the generated skill code.";
        lastHint = "Include the file_path in the second line of the script.";
        continue;
      } else {
        console.log(`👀 Suggested new skill file path: ${saveFilePath}`);
      }
      console.log(`⏳️ Testing new skill...`);
      await skillModule.default();
      console.log(`🎉🎉🎉 New skill tested successfully 🎉🎉🎉`);

      // スキルをファイルとして保存
      console.log(`⏳️ Saving new skill to file: ${saveFilePath}`);
      // まず、 saveFilePath までのディレクトリが存在することを確認
      // src/lib/skills/populationDensity/JapanHigherThanChina.ts みたいなファイルパスのはず
      // ディレクトリが存在しなかったらメチャクチャなことをやろうとしているので、エラーを出す
      const saveDir = path.join(
        __dirname,
        `../../${path.dirname(saveFilePath)}`
      );
      try {
        await fs.access(saveDir);
      } catch (error) {
        console.error(
          `❌ Failed to save new skill: directory not found: ${saveDir}`
        );
        continue;
      }
      await fs.writeFile(
        path.join(__dirname, `../../${saveFilePath}`),
        skillCode
      );
      console.log(`💾 New skill saved to file: ${saveFilePath}`);

      // スキルをデータベースに保存
      const newSkill = await saveSkillToDatabase(taskDescription, skillCode);
      console.log(`💾 Skill saved to database for task: ${taskDescription}`);
      return newSkill; // 成功
    } catch (error) {
      if (error instanceof Error) {
        console.error(`❌ Skill execution failed:`);
        lastCode = skillCode.replaceAll("{", "{{").replaceAll("}", "}}");
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
        console.error(error.message);
        console.debug("----- ----- -----");
        console.log(skillCode);
        console.debug("----- ----- -----");
        lastError = JSON.stringify(error, replaceErrors, 2)
          .replaceAll("{", "{{")
          .replaceAll("}", "}}");
        if (error instanceof Error) {
          if (error.message.includes("Overpass")) {
            lastHint = `Try to fix Overpass QL.
For example:
- Change name to name:en only failed Overpass QL.
`;
          } else {
            lastHint = null;
          }
        }
      }
    }
  }

  console.error(
    "⚠️  Failed to generate a working skill after multiple attempts."
  );
  throw new Error(
    "Failed to generate a working skill after multiple attempts."
  );
};
