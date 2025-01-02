// src/main.ts
import { prisma } from "./db";
import { promises as fs } from "fs";
import path from "path";

(async () => {
  console.log("🗺️  Geo-Voyager Starting...");

  // OPENなQuestionを1件取得
  const question = await prisma.question.findFirst({
    where: { status: "OPEN" },
  });
  if (!question) {
    console.log("No OPEN questions found.");
    return;
  } else {
    console.log(`❓️ Question: ${question.description}`);
  }

  // OPENなQuestionに関連し、PENDINGなHypothesisを1件取得
  const hypothesis = await prisma.hypothesis.findFirst({
    where: {
      status: "PENDING",
      questionId: question.id,
    },
  });
  if (!hypothesis) {
    console.log("No PENDING hypotheses found for this question.");
    return;
  } else {
    console.log(`💡 Hypothesis: ${hypothesis.description}`);
  }

  // Hypothesisに結びついているすべてのTaskを取得
  const tasks = await prisma.task.findMany({
    where: {
      hypotheses: {
        some: {
          hypothesisId: hypothesis.id,
        },
      },
    },
  });
  if (tasks.length === 0) {
    console.log("No tasks associated with this hypothesis.");
    return;
  }

  console.log("📝 Associated Tasks:");
  for (const task of tasks) {
    if (task.status === "COMPLETED") {
      console.log(
        `  - ✅ Task: ${task.description} already completed with result: ${task.result}`
      );
      continue;
    }
    if (task.status === "FAILED") {
      console.log(
        `  - ❌ Task: ${task.description} failed with error: ${task.result}`
      );
      continue;
    }
    if (task.status === "PENDING") {
      console.log(`  - 🔨 Starting task: ${task.description}`);

      // スキルを取得
      const skill = await prisma.skill.findFirst({
        where: {
          description: task.description,
        },
      });

      if (skill) {
        console.log(`    - 🎁 Skill found: ${skill.description}`);

        // 保存先ディレクトリとファイルパスを設定
        const tempDir = path.join(__dirname, "./tmp/skills");
        const tempFilePath = path.join(tempDir, `${skill.id}.ts`);

        // 一時ディレクトリを作成（存在しない場合のみ）
        await fs.mkdir(tempDir, { recursive: true });

        // スキルコードを一時ファイルに保存
        await fs.writeFile(tempFilePath, skill.code);

        let status;
        let result;
        try {
          // 動的にスキルをインポート
          const skillModule = await import(`file://${tempFilePath}`);
          if (skillModule.default) {
            result = await skillModule.default();
            // trueなら仮説は引き続き支持される。falseなら仮説は棄却される。
            if (result) {
              console.log(`    - ✅ Result: ${result}`);
              status = "COMPLETED";
            } else {
              console.log(`    - ❌ Result: ${result}`);
              status = "FAILED";
              // hypothesisのstatusをREJECTEDに更新
              await prisma.hypothesis.update({
                where: { id: hypothesis.id },
                data: { status: "REJECTED" },
              });
            }
          } else {
            console.error("    - ⚠️  No default export found in skill.");
            status = "FAILED";
            result = "No default export found in skill.";
          }
        } catch (error) {
          console.error("    - ⚠️  Error executing skill:", error);
          status = "FAILED";
          result = (error as Error).message;
        } finally {
          await prisma.task.update({
            where: { id: task.id },
            data: {
              status,
              result: result.toString(),
            },
          });
          // 一時ファイルを削除
          await fs.unlink(tempFilePath);
        }
      } else {
        console.error("    - ⚠️  Skill not found for task.");
      }
    }
  }
})();
