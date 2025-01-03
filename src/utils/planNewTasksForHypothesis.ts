import { Hypothesis } from "@prisma/client";
import { createTaskByHypothesisId, getAllExecutedTasks } from "../db/task";
import { ChatOllama } from "@langchain/ollama";

/**
 * 仮説に関連付けられた新しいタスクを計画・作成
 * @param hypothesis 新しい仮説
 */
export const planNewTasksForHypothesis = async (hypothesis: Hypothesis) => {
  console.log("🛠️ Planning new tasks for the hypothesis...");

  // 仮説を検証するためのタスク
  const taskList: string[] = [];

  const executedTasks = await getAllExecutedTasks();
  const prompt = `Given the hypothesis: "${
    hypothesis.description
  }", plan new tasks to test the hypothesis in Japanese.

Executable tasks for example:
${executedTasks.map((t) => `- ${t.description}`).join("\n")}

Reply with only a list of possible executable tasks, separated by newlines.`;

  // console.log("🤖 Tasks generation prompt:");
  // console.log(prompt);

  // AIのレスポンスとして新しいタスクを生成
  const model = new ChatOllama({
    model: "qwen2.5:7b",
    temperature: 0,
  });
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
