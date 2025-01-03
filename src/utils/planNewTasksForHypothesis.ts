import { Hypothesis } from "@prisma/client";
import { createTaskByHypothesisId, getAllExecutedTasks } from "../db/task";
import { ChatOllama } from "@langchain/ollama";

/**
 * 仮説に関連付けられた新しいタスクを計画・作成
 * @param hypothesis 新しい仮説
 */
export const planNewTasksForHypothesis = async (hypothesis: Hypothesis) => {
  console.log("🧠 Planning new tasks for the hypothesis...");
  const model = new ChatOllama({
    model: "qwen2.5:7b",
    temperature: 0,
    repeatPenalty: 1.1,
  });

  // 仮説を検証するためのタスク
  const taskList: string[] = [];

  const executedTasks = await getAllExecutedTasks();

  /**
== Case study ==
Hypothesis: 世界で最も人口密度が高い国はシンガポールである。
Wrong task: シンガポールの人口密度がモナコよりも低いことを確認する。
Reason: If the task result is false, it does not reject the hypothesis.
Wrong task: シンガポールの人口を他の国と比較する。
Reason: The task is inexecutable. And it is not a true/false question.
Correct task1: シンガポールの人口密度がモナコよりも高いことを確認する。
Correct task2: モナコの人口密度がシンガポールよりも低いことを確認する。

Hypothesis: 東京都において、学校の数が最も多い行政区は新宿区である。
Wrong task: 東京都内での学校数を新宿区と他の行政区に比較する。
Reason: The task is inexecutable. And it is not a true/false question.
Wrong task: 新宿区の学校数が東京都内で最多であることを確認する。
Reason: The task is inexecutable. The task should be most detailed possible and executable step-by-step.
Wrong task: 板橋区の学校の数が他のすべての行政区の学校数よりも多いことを確認する。
Reason: The task is leapfrog. The task should be most detailed possible and executable step-by-step.
Wrong task: 東京都文京区の学校の数が他のすべての行政区の学校数よりも多いことを確認する。
Reason: The task is leapfrog. The task should be most detailed possible and executable step-by-step.
 */

  const prompt = `Given the hypothesis: "${
    hypothesis.description
  }", plan new executable tasks to test the hypothesis in Japanese.

The task must be answerable with a "true" or "false" response.
The task must reject the hypothesis if the result is false.
Must not plan leapfrog inexecutable tasks.

Must not plan tasks that are already executed or failed.

Examples of executable tasks:
${executedTasks.map((t) => `- ${t.description} [${t.status}]`).join("\n")}

Reply with only a list of possible new executable tasks, separated by newlines.`;

  // console.log("🤖 Tasks generation prompt:");
  // console.log(prompt);

  // AIのレスポンスとして新しいタスクを生成
  const response = await model.invoke(prompt);
  const content = response.content as string;
  const lines = content.split("\n");
  for (const line of lines) {
    const task = line.trim();
    if (task.length > 0) {
      taskList.push(task);
    }
  }

  const tasks = [];
  // タスクをデータベースに作成
  for (let taskDescription of taskList) {
    // 先頭に "- " がある場合には、除去する
    if (taskDescription.startsWith("- ")) {
      taskDescription = taskDescription.slice(2);
    }
    // 。で終わっていない場合は無視する
    if (!taskDescription.endsWith("。")) {
      console.error(`⚠️  Ignoring task: ${taskDescription}`);
      continue;
    }
    console.log(`💾 Saving new task: ${taskDescription}`);
    const newTask = await createTaskByHypothesisId(
      hypothesis.id,
      taskDescription
    );
    tasks.push(newTask);
  }

  console.log(`📋️ Planned total ${tasks.length} new tasks.`);
  return tasks;
};
