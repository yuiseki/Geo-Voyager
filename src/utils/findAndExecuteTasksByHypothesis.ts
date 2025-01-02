// src/utils/findAndExecuteTasksByHypothesis.ts
import { promises as fs } from "fs";
import path from "path";
import { Hypothesis } from "@prisma/client";
import {
  getAllTasksByHypothesisId,
  TaskStatus,
  updateTaskStatusAndResult,
} from "../db/task";
import { getFirstSkillByDescription } from "../db/skill";
import { HypothesisStatus, updateHypothesisStatus } from "../db/hypothesis";
import { planNewTasksForHypothesis } from "./planNewTasksForHypothesis";

export const findAndExecuteTasksByHypothesis = async (
  hypothesis: Hypothesis
) => {
  // Hypothesisに結びついているすべてのTaskを取得
  let tasks = await getAllTasksByHypothesisId(hypothesis.id);
  if (tasks.length === 0) {
    console.log("⚠️  No tasks associated with this hypothesis.");
    tasks = await planNewTasksForHypothesis(hypothesis);
  }

  console.log("📋 Associated Tasks:");
  for (const task of tasks) {
    if (task.status === "COMPLETED") {
      console.log(
        `  - ✅ Task: ${task.description} already completed with result: ${task.result}`
      );
      continue;
    }
    if (task.status === "FAILED") {
      console.log(
        `  - ❌ Task: ${task.description} failed with result: ${task.result}`
      );
      break;
    }
    if (task.status === "ERROR") {
      console.log(
        `  - 🚫 Task: ${task.description} errored with message: ${task.result}`
      );
      continue;
    }
    if (task.status === "PENDING") {
      console.log(`  - 🔨 Starting task: ${task.description}`);

      // スキルを取得
      const skill = await getFirstSkillByDescription(task.description);

      if (skill) {
        console.log(`    - 🎁 Skill found: ${skill.description}`);
        // 保存先ディレクトリとファイルパスを設定
        const tempDir = path.join(__dirname, "tmp", "skills");
        const tempFilePath = path.join(tempDir, `${skill.id}.ts`);
        // 一時ディレクトリを作成（存在しない場合のみ）
        await fs.mkdir(tempDir, { recursive: true });
        // スキルコードを一時ファイルに保存
        await fs.writeFile(tempFilePath, skill.code);

        let status;
        let result;
        try {
          // 動的にスキルをインポートして実行
          const skillModule = await import(`file://${tempFilePath}`);
          if (skillModule.default) {
            result = await skillModule.default();
            // trueなら仮説は引き続き支持される
            // falseなら仮説は棄却される
            if (result) {
              console.log(`      - ✅ Result: ${result}`);
              status = TaskStatus.COMPLETED;
            } else {
              console.log(`      - ❌ Result: ${result}, hypothesis rejected.`);
              status = TaskStatus.FAILED;
              // hypothesisのstatusをREJECTEDに更新
              await updateHypothesisStatus(
                hypothesis.id,
                HypothesisStatus.REJECTED
              );
              break;
            }
          } else {
            console.error("      - 🚫 No default export found in skill.");
            status = TaskStatus.ERROR;
            result = "No default export found in skill.";
          }
        } catch (error) {
          console.error("      - 🚫 Error executing skill:", error);
          status = TaskStatus.ERROR;
          result = (error as Error).message;
        } finally {
          // taskのstatusとresultを更新
          if (status) {
            await updateTaskStatusAndResult(task.id, status, result.toString());
          }
          // 一時ファイルを削除
          await fs.unlink(tempFilePath);
        }
      } else {
        console.error("    - 🚫 Skill not found for task.");
      }
    }
  }
};
