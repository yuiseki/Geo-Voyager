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
import { generateNewSkillForTask } from "./generateSkillForTask";
import {
  getQuestionById,
  QuestionStatus,
  updateQuestionStatus,
} from "../db/question";

export const findAndExecuteTasksByHypothesis = async (
  hypothesis: Hypothesis
) => {
  // Hypothesisに結びついているすべてのTaskを取得
  let tasks = await getAllTasksByHypothesisId(hypothesis.id);
  if (tasks.length === 0) {
    console.log("⚠️  No tasks associated with this hypothesis.");
    // タスクが無かったら新しいタスクを計画する
    tasks = await planNewTasksForHypothesis(hypothesis);
  }

  // すべてのタスクがCOMPLETEDの場合
  if (tasks.every((task) => task.status === "COMPLETED")) {
    console.log("🎉 All tasks for this hypothesis has completed.");
    if (tasks.length < 20) {
      // タスクの計画を再度行う
      tasks = await planNewTasksForHypothesis(hypothesis);
    } else {
      console.log("🎉 Hypothesis has been verified.");
      // 仮説をACCEPTEDに更新
      await updateHypothesisStatus(hypothesis.id, HypothesisStatus.VERIFIED);
      // 疑問をSOLVEDに更新
      if (hypothesis.questionId) {
        const question = await getQuestionById(hypothesis.questionId);
        if (question) {
          await updateQuestionStatus(question.id, QuestionStatus.SOLVED);
        }
        console.log("🎉 Question has been solved.");
      }
      return;
    }
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

      // 仮説検証タスクを実行するためのスキルを取得
      let skill = await getFirstSkillByDescription(task.description);
      if (!skill) {
        // スキルがなかったら新しいスキルの生成を試みる
        try {
          skill = await generateNewSkillForTask(task.description);
        } catch (error) {
          console.error("    - 🚫 Error generating skill:", error);
          await updateTaskStatusAndResult(
            task.id,
            TaskStatus.ERROR,
            (error as Error).message
          );
          continue;
        }
      }

      if (skill) {
        // スキルがあったら実行する
        console.log(`    - 🎁 Skill found: ${skill.description}`);
        let attempts = 0;
        const maxAttempts = 5;
        const sleep = await new Promise((resolve) => setTimeout(resolve, 5000));
        while (attempts < maxAttempts) {
          // 一時保存先ディレクトリとファイルパスを設定
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
                break;
              } else {
                console.log(
                  `      - ❌ Result: ${result}, hypothesis rejected.`
                );
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
            if (attempts === maxAttempts) {
              status = TaskStatus.ERROR;
              result = (error as Error).message;
              break;
            } else {
              console.log("      - 🔁 Retrying in 5 seconds...");
              attempts++;
              await sleep;
              continue;
            }
          } finally {
            // 一時ファイルを削除
            await fs.unlink(tempFilePath);
            // taskのstatusとresultを更新
            if (status) {
              await updateTaskStatusAndResult(
                task.id,
                status,
                result.toString()
              );
            }
          }
        }
      }
    }
  }
};
