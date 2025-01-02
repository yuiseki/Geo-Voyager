import { PrismaClient } from "@prisma/client";

const prisma = new PrismaClient();

/*
東京都においては、人口密度が高い行政区ほど、1人当たりの公園面積が小さい。
東京都においては、鉄道路線の数が多い行政区ほど、駅の密度も高い。
東京都においては、行政区の面積が広いほど、学校の数が多い。
東京都においては、行政区の面積が広いほど、病院の数が多い。
東京都においては、行政区の面積が広いほど、図書館の数が多い。
東京都においては、行政区の面積が広いほど、公園の数が多い。
東京都においては、商業施設の多い行政区ほど、駐車場の数が多い。
東京都においては、駅の密度が高い行政区ほど、自転車駐輪場が多い。
東京都においては、駅の密度が高い行政区ほど、商業施設が多い。
*/

async function main() {
  // Questionの作成
  const question = await prisma.question.create({
    data: {
      description: "世界で最も人口密度が高い国はどこだろう？",
      status: "OPEN",
    },
  });

  // Hypothesisの作成
  const hypothesis = await prisma.hypothesis.create({
    data: {
      description: "世界で最も人口密度が高い国はモナコである。",
      status: "PENDING",
      questionId: question.id, // Questionとの関連付け
    },
  });

  // Tasksの作成
  await prisma.task.createMany({
    data: [
      {
        description: "モナコの面積と人口を得て、人口密度を計算する",
        status: "PENDING",
      },
      {
        description: "シンガポールの面積と人口を得て、人口密度を計算する",
        status: "PENDING",
      },
      {
        description: "モナコの人口密度とシンガポールの人口密度を比較する",
        status: "PENDING",
      },
      {
        description: "マカオの面積と人口を得て、人口密度を計算する",
        status: "PENDING",
      },
      {
        description: "モナコの人口密度とマカオの人口密度を比較する",
        status: "PENDING",
      },
    ],
  });

  // HypothesisとTasksの関連付け
  const tasksData = await prisma.task.findMany({
    where: { status: "PENDING" },
  });

  for (const task of tasksData) {
    await prisma.hypothesisTask.create({
      data: {
        hypothesisId: hypothesis.id,
        taskId: task.id,
      },
    });
  }

  console.log("Seed data has been added successfully.");
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
