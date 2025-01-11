// src/utils/findAndExecuteTasksByHypothesis.ts
import { promises as fs } from "fs";
import path from "path";
import { Question } from "@prisma/client";
import {
  getAllTasksByQuestionId,
  TaskStatus,
  updateTaskStatusAndResult,
} from "../db/task";
import { getFirstSkillByDescription, saveSkillToDatabase } from "../db/skill";
import { planNewTasksForHypothesis as planNewTasksForQuestion } from "./planNewTasksForQuestion";
import { generateNewSkillForTask } from "./generateSkillForTask";
import {
  getQuestionById,
  QuestionStatus,
  updateQuestionStatus,
} from "../db/question";
import { glob } from "glob";
import { prisma } from "../db";

export const findAndExecuteTasksByQuestion = async (question: Question) => {
  // question に結びついているすべてのTaskを取得
  let tasks = await getAllTasksByQuestionId(question.id);
  if (tasks.length === 0) {
    console.log("⚠️  No tasks associated with this question.");
    // タスクが無かったら新しいタスクを計画する
    tasks = await planNewTasksForQuestion(question);
  }

  // すべてのタスクがCOMPLETEDの場合
  if (tasks.every((task) => task.status === "COMPLETED")) {
    console.log("🎉 All tasks for this question has completed.");
    if (tasks.length < 1) {
      // タスクの計画を再度行う
      tasks = await planNewTasksForQuestion(question);
    } else {
      console.log("🎉 Question has been solved.");
      // 仮説をACCEPTEDに更新
      await updateQuestionStatus(question.id, QuestionStatus.SOLVED);
      // 疑問をSOLVEDに更新
      if (question.id) {
        await updateQuestionStatus(question.id, QuestionStatus.SOLVED);
        console.log("🎉 Question has been solved.");
      }
      return;
    }
  }

  console.log("📋 Associated Tasks:");
  for (const task of tasks) {
    if (task.description.includes("蓬爾")) {
      console.log("🚫 Task contains 蓬爾, invalid!");
      // Taskを削除
      await prisma.task.delete({
        where: { id: task.id },
      });
      continue;
    }
    if (task.status === "COMPLETED") {
      console.log(
        `  - ✅ Task: ${task.description} [${task.result?.toUpperCase()}]`
      );
      continue;
    }
    if (task.status === "FAILED") {
      console.log(
        `  - ❌ Task: ${task.description} [${task.result?.toUpperCase()}]`
      );
      break;
    }
    if (task.status === "ERROR") {
      console.log(
        `  - 🚫 Task: ${task.description} ${task.result?.toUpperCase}`
      );
      continue;
    }
    if (task.status === "PENDING") {
      console.log(`  - 🔨 Starting task: ${task.description}`);

      // 仮説検証タスクを実行するためのスキルを取得
      let skill = await getFirstSkillByDescription(task.description);

      if (skill === null) {
        // src/lib/skills/**/*.ts 以下のスキルを探す
        const skillFiles = await glob(
          path.join(__dirname, "../lib/skills/**/*.ts")
        );
        for await (const file of skillFiles) {
          const fileContent = await fs.readFile(file, "utf-8");
          const lines = fileContent.split("\n");
          // 一行目からdescriptionを抽出
          const descriptionMatch = lines[0].match(/\/\/ description: (.+)/);
          if (!descriptionMatch) {
            console.warn(`No description found in ${file}`);
            continue;
          }
          const description = descriptionMatch[1].trim();
          if (description === task.description) {
            skill = await saveSkillToDatabase(description, fileContent);
          }
        }
      }

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
        let result;
        let attempts = 0;
        const maxAttempts = 5;
        while (attempts < maxAttempts) {
          // 一時保存先ディレクトリとファイルパスを設定
          const tempDir = path.join(__dirname, "tmp", "skills");
          const tempFilePath = path.join(tempDir, `${skill.id}.ts`);
          // 一時ディレクトリを作成（存在しない場合のみ）
          await fs.mkdir(tempDir, { recursive: true });
          // スキルコードを一時ファイルに保存
          await fs.writeFile(tempFilePath, skill.code);

          let status;
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
                // questionのstatusをUNRESOLVABLEに更新
                await updateQuestionStatus(
                  question.id,
                  QuestionStatus.UNRESOLVABLE
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
              const sleep = () =>
                new Promise((resolve) => setTimeout(resolve, 5000));
              await sleep();
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
        if (result === false) {
          console.log("🚫 Hypothesis rejected.");
          break;
        }
      }
    }
  }
};
