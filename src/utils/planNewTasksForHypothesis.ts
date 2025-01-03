import { Hypothesis } from "@prisma/client";
import { createTaskByHypothesisId, getAllExecutedTasks } from "../db/task";
import { ChatOllama } from "@langchain/ollama";

/**
 * 仮説に関連付けられた新しいタスクを計画・作成
 * @param hypothesis 新しい仮説
 */
export const planNewTasksForHypothesis = async (hypothesis: Hypothesis) => {
  console.log("🛠️ Planning new tasks for the hypothesis...");
  const model = new ChatOllama({
    model: "qwen2.5:7b",
    temperature: 0,
  });

  // 仮説を検証するためのタスク
  const taskList: string[] = [];

  const executedTasks = await getAllExecutedTasks();
  const prompt = `Given the hypothesis: "${
    hypothesis.description
  }", plan new executable tasks to test the hypothesis in Japanese.

The task must be answerable with a "true" or "false" response.
The task must reject the hypothesis if the result is false.
Must not plan leapfrog inexecutable tasks.

Examples of executable tasks:
${executedTasks.map((t) => `- ${t.description}`).join("\n")}

== Case study ==
Hypothesis: 世界で最も人口密度が高い国はシンガポールである。
Wrong task: シンガポールの人口密度がモナコよりも低いことを確認する。
Reason: If the task result is false, it does not reject the hypothesis.
Correct task1: シンガポールの人口密度がモナコよりも高いことを確認する。
Correct task2: モナコの人口密度がシンガポールよりも低いことを確認する。

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
