import { Question } from "@prisma/client";
import { createTaskByQuestionId, getAllExecutedTasks } from "../db/task";
import { ChatOllama } from "@langchain/ollama";

/**
 * 仮説に関連付けられた新しいタスクを計画・作成
 * @param question 新しい仮説
 */
export const planNewTasksForHypothesis = async (question: Question) => {
  console.log("🤖 Planning new tasks for the question...");
  const model = new ChatOllama({
    model: "qwen2.5:7b",
    temperature: 0.1,
  });

  // 仮説を検証するためのタスク
  const taskList: string[] = [];

  const executedTasks = await getAllExecutedTasks();

  const prompt = `Given the hypothesis: "${
    question.description
  }", plan new executable tasks to test the hypothesis in Japanese.

The task must be answerable with a "true" or "false" response.
The task must reject the hypothesis if the result is false.
Must not plan leapfrog inexecutable tasks.

Must not plan tasks that are already executed or failed.

Examples of executable tasks:
${executedTasks
  .slice(0, 10)
  .map((t) => `- ${t.description} [${t.status}]`)
  .join("\n")}

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
    // 「など」が含まれている場合は無視する
    if (taskDescription.includes("など")) {
      console.error(`⚠️  Ignoring task: ${taskDescription}`);
      continue;
    }
    // 「他の」が含まれている場合は無視する
    if (taskDescription.includes("他の")) {
      console.error(`⚠️  Ignoring task: ${taskDescription}`);
      continue;
    }
    // 「すべて」が含まれている場合は無視する
    if (taskDescription.includes("すべて")) {
      console.error(`⚠️  Ignoring task: ${taskDescription}`);
      continue;
    }
    // 「全て」が含まれている場合は無視する
    if (taskDescription.includes("全て")) {
      console.error(`⚠️  Ignoring task: ${taskDescription}`);
      continue;
    }
    // 「低い」が含まれている場合は無視する
    if (taskDescription.includes("低い")) {
      console.error(`⚠️  Ignoring task: ${taskDescription}`);
      continue;
    }
    // 蓬爾問題
    if (taskDescription.includes("蓬爾")) {
      console.log("🚫 Task contains 蓬爾, invalid!");
      continue;
    }
    console.log(`💾 Saving new task: ${taskDescription}`);
    const newTask = await createTaskByQuestionId(question.id, taskDescription);
    tasks.push(newTask);
  }

  console.log(`📋️ Planned total ${tasks.length} new tasks.`);
  // if (tasks.length > 0) {
  //   process.exit(0);
  // }
  return tasks;
};
