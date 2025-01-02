import { Hypothesis } from "@prisma/client";
import { createTaskByHypothesisId } from "../db/task";

/**
 * 仮説に関連付けられた新しいタスクを計画・作成
 * @param hypothesis 新しい仮説
 */
export const planNewTasksForHypothesis = async (hypothesis: Hypothesis) => {
  console.log("🛠️ Planning new tasks for the hypothesis...");

  // 仮説に基づいて計画するタスク
  const taskList = [];

  if (hypothesis.description.includes("シンガポール")) {
    taskList.push(
      "シンガポールの人口と面積を取得し、人口密度を計算する",
      "モナコの人口と面積を取得し、人口密度を計算する",
      "シンガポールとモナコの人口密度を比較する"
    );
  } else if (hypothesis.description.includes("バーレーン")) {
    taskList.push(
      "バーレーンの人口と面積を取得し、人口密度を計算する",
      "モナコの人口と面積を取得し、人口密度を計算する",
      "バーレーンとモナコの人口密度を比較する"
    );
  } else {
    taskList.push("新しい国の人口と面積を取得し、モナコとの比較を行う");
  }

  const tasks = [];
  // タスクをデータベースに作成
  for (const taskDescription of taskList) {
    const newTask = await createTaskByHypothesisId(
      hypothesis.id,
      taskDescription
    );
    tasks.push(newTask);
  }

  console.log(`📋️ Planed new ${tasks.length} tasks.`);
  return tasks;
};
