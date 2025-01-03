import { PrismaClient } from "@prisma/client";
import fs from "fs";
import path from "path";
import { glob } from "glob";

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

const seedQuestionWhichCountryIsMostHighestPopulationDensity = async () => {
  // Question1の作成
  const question1 = await prisma.question.create({
    data: {
      description: "世界で最も人口密度が高い国はどこだろう？",
      status: "OPEN",
    },
  });

  // Hypothesis1の作成
  const hypothesis1 = await prisma.hypothesis.create({
    data: {
      description: "世界で最も人口密度が高い国はモナコである。",
      status: "PENDING",
      questionId: question1.id, // Questionとの関連付け
    },
  });
  // Taskの作成
  const task1ForHypothesis1 = await prisma.task.create({
    data: {
      description: "モナコの人口密度がシンガポールよりも高いことを確認する。",
      status: "PENDING",
    },
  });
  // Hypothesis1とTasksの関連付け
  await prisma.hypothesisTask.create({
    data: {
      hypothesisId: hypothesis1.id,
      taskId: task1ForHypothesis1.id,
    },
  });

  // Hypothesis2の作成
  const hypothesis2 = await prisma.hypothesis.create({
    data: {
      description: "世界で最も人口密度が高い国はシンガポールである。",
      status: "PENDING",
      questionId: question1.id, // Questionとの関連付け
    },
  });
  // Taskの作成
  const task1ForHypothesis2 = await prisma.task.create({
    data: {
      description: "シンガポールの人口密度がモナコよりも高いことを確認する。",
      status: "PENDING",
    },
  });
  // Hypothesis2とTasksの関連付け
  await prisma.hypothesisTask.create({
    data: {
      hypothesisId: hypothesis2.id,
      taskId: task1ForHypothesis2.id,
    },
  });
  // Taskの作成
  const task2ForHypothesis2 = await prisma.task.create({
    data: {
      description: "シンガポールの人口密度が日本よりも高いことを確認する。",
      status: "PENDING",
    },
  });
  // Hypothesis2とTasksの関連付け
  await prisma.hypothesisTask.create({
    data: {
      hypothesisId: hypothesis2.id,
      taskId: task2ForHypothesis2.id,
    },
  });
  // Taskの作成
  const task3ForHypothesis2 = await prisma.task.create({
    data: {
      description:
        "シンガポールの人口密度がバーレーンよりも高いことを確認する。",
      status: "PENDING",
    },
  });
  // Hypothesis2とTasksの関連付け
  await prisma.hypothesisTask.create({
    data: {
      hypothesisId: hypothesis2.id,
      taskId: task3ForHypothesis2.id,
    },
  });
  // Taskの作成
  const task4ForHypothesis2 = await prisma.task.create({
    data: {
      description:
        "シンガポールの人口密度がモルディブよりも高いことを確認する。",
      status: "PENDING",
    },
  });
  // Hypothesis2とTasksの関連付け
  await prisma.hypothesisTask.create({
    data: {
      hypothesisId: hypothesis2.id,
      taskId: task4ForHypothesis2.id,
    },
  });
};

const seedQuestionWhichWardInTokyoHasMostNumberOfSchools = async () => {
  // Question1の作成
  const question1 = await prisma.question.create({
    data: {
      description: "東京都において、学校の数が最も多い行政区はどこだろう？",
      status: "OPEN",
    },
  });

  // Hypothesis1の作成
  const hypothesis1 = await prisma.hypothesis.create({
    data: {
      description: "東京都において、学校の数が最も多い行政区は千代田区である。",
      status: "PENDING",
      questionId: question1.id, // Questionとの関連付け
    },
  });
  // Taskの作成
  const task1ForHypothesis1 = await prisma.task.create({
    data: {
      description:
        "東京都千代田区の学校の数が東京都港区よりも多いことを確認する。",
      status: "PENDING",
    },
  });
  // Hypothesis1とTasksの関連付け
  await prisma.hypothesisTask.create({
    data: {
      hypothesisId: hypothesis1.id,
      taskId: task1ForHypothesis1.id,
    },
  });

  // Hypothesis2の作成
  const hypothesis2 = await prisma.hypothesis.create({
    data: {
      description: "東京都において、学校の数が最も多い行政区は港区である。",
      status: "PENDING",
      questionId: question1.id, // Questionとの関連付け
    },
  });
  // Taskの作成
  const task1ForHypothesis2 = await prisma.task.create({
    data: {
      description:
        "東京都港区の学校の数が東京都千代田区よりも多いことを確認する。",
      status: "PENDING",
    },
  });
  // Hypothesis2とTasksの関連付け
  await prisma.hypothesisTask.create({
    data: {
      hypothesisId: hypothesis2.id,
      taskId: task1ForHypothesis2.id,
    },
  });
  // Taskの作成
  const task2ForHypothesis2 = await prisma.task.create({
    data: {
      description:
        "東京都港区の学校の数が東京都新宿区よりも多いことを確認する。",
      status: "PENDING",
    },
  });
  // Hypothesis2とTasksの関連付け
  await prisma.hypothesisTask.create({
    data: {
      hypothesisId: hypothesis2.id,
      taskId: task2ForHypothesis2.id,
    },
  });
  // Taskの作成
  const task3ForHypothesis2 = await prisma.task.create({
    data: {
      description:
        "東京都港区の学校の数が東京都文京区よりも多いことを確認する。",
      status: "PENDING",
    },
  });
  // Hypothesis2とTasksの関連付け
  await prisma.hypothesisTask.create({
    data: {
      hypothesisId: hypothesis2.id,
      taskId: task3ForHypothesis2.id,
    },
  });
};

const seedSkills = async () => {
  // src/lib/skills/**/*.ts ファイルをすべて取得
  const skillFiles = await glob(
    path.join(__dirname, "../src/lib/skills/**/*.ts")
  );

  for (const file of skillFiles) {
    const fileContent = fs.readFileSync(file, "utf-8");
    const lines = fileContent.split("\n");

    // 一行目からdescriptionを抽出
    const descriptionMatch = lines[0].match(/\/\/ description: (.+)/);
    if (!descriptionMatch) {
      console.warn(`No description found in ${file}`);
      continue;
    }
    const description = descriptionMatch[1].trim();

    // ファイル全体をコードとしてセット
    const code = fileContent;

    // Skillをデータベースに保存
    await prisma.skill.create({
      data: {
        description,
        code,
      },
    });
  }
};

async function main() {
  console.log("Seeding...");

  await seedQuestionWhichCountryIsMostHighestPopulationDensity();
  await seedQuestionWhichWardInTokyoHasMostNumberOfSchools();
  await seedSkills();
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
