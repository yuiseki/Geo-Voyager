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
  // Questionの作成
  const question = await prisma.question.create({
    data: {
      description: "世界で最も人口密度が高い国はどこだろう？",
      status: "OPEN",
    },
  });

  // HypothesisWrongの作成
  const hypothesisWrong = await prisma.hypothesis.create({
    data: {
      description: "世界で最も人口密度が高い国はシンガポールである。",
      status: "PENDING",
      questionId: question.id, // Questionとの関連付け
    },
  });
  // Taskの作成
  const taskForHypothesisWrong = await prisma.task.create({
    data: {
      description:
        "世界で最も人口密度の高い国がシンガポールであることを確認する。",
      status: "PENDING",
    },
  });
  // HypothesisとTasksの関連付け
  await prisma.hypothesisTask.create({
    data: {
      hypothesisId: hypothesisWrong.id,
      taskId: taskForHypothesisWrong.id,
    },
  });

  // HypothesisAnswerの作成
  const hypothesisAnswer = await prisma.hypothesis.create({
    data: {
      description: "世界で最も人口密度が高い国はモナコである。",
      status: "PENDING",
      questionId: question.id, // Questionとの関連付け
    },
  });
  // Taskの作成
  const taskForHypothesisAnswer = await prisma.task.create({
    data: {
      description: "世界で最も人口密度の高い国がモナコであることを確認する。",
      status: "PENDING",
    },
  });
  // HypothesisとTasksの関連付け
  await prisma.hypothesisTask.create({
    data: {
      hypothesisId: hypothesisAnswer.id,
      taskId: taskForHypothesisAnswer.id,
    },
  });
};

const seedQuestionWhichWardsInTokyoIsMostHighestPopulationDensity =
  async () => {
    // Questionの作成
    const question = await prisma.question.create({
      data: {
        description: "東京都において、人口密度が最も高い行政区はどこだろう？",
        status: "OPEN",
      },
    });
    // HypothesisWrongの作成
    const hypothesisWrong = await prisma.hypothesis.create({
      data: {
        description:
          "東京都において、人口密度が最も高い行政区は千代田区である。",
        status: "PENDING",
        questionId: question.id, // Questionとの関連付け
      },
    });
    // Taskの作成
    const taskForHypothesisWrong = await prisma.task.create({
      data: {
        description:
          "東京都において、人口密度が最も高い行政区が千代田区であることを確認する。",
        status: "PENDING",
      },
    });
    // HypothesisとTasksの関連付け
    await prisma.hypothesisTask.create({
      data: {
        hypothesisId: hypothesisWrong.id,
        taskId: taskForHypothesisWrong.id,
      },
    });
    // HypothesisAnswerの作成
    const hypothesisAnswer = await prisma.hypothesis.create({
      data: {
        description: "東京都において、人口密度が最も高い行政区は豊島区である。",
        status: "PENDING",
        questionId: question.id, // Questionとの関連付け
      },
    });
    // Taskの作成
    const taskForHypothesisAnswer = await prisma.task.create({
      data: {
        description:
          "東京都において、人口密度が最も高い行政区が豊島区であることを確認する。",
        status: "PENDING",
      },
    });
    // HypothesisとTasksの関連付け
    await prisma.hypothesisTask.create({
      data: {
        hypothesisId: hypothesisAnswer.id,
        taskId: taskForHypothesisAnswer.id,
      },
    });
  };

const seedQuestionWhichWardsInTokyoIsMostHospitals = async () => {
  // Questionの作成
  const question = await prisma.question.create({
    data: {
      description: "東京都において、病院が最も多い行政区はどこだろう？",
      status: "OPEN",
    },
  });
  // HypothesisWrongの作成
  const hypothesisWrong = await prisma.hypothesis.create({
    data: {
      description: "東京都において、病院が最も多い行政区は江東区である。",
      status: "PENDING",
      questionId: question.id, // Questionとの関連付け
    },
  });
  // Taskの作成
  const taskForHypothesisWrong = await prisma.task.create({
    data: {
      description:
        "東京都において、病院が最も多い行政区が江東区であることを確認する。",
      status: "PENDING",
    },
  });
  // HypothesisとTasksの関連付け
  await prisma.hypothesisTask.create({
    data: {
      hypothesisId: hypothesisWrong.id,
      taskId: taskForHypothesisWrong.id,
    },
  });
  // HypothesisAnswerの作成
  const hypothesisAnswer = await prisma.hypothesis.create({
    data: {
      description: "東京都において、病院が最も多い行政区は多摩市である。",
      status: "PENDING",
      questionId: question.id, // Questionとの関連付け
    },
  });
  // Taskの作成
  const taskForHypothesisAnswer = await prisma.task.create({
    data: {
      description:
        "東京都において、病院が最も多い行政区が多摩市であることを確認する。",
      status: "PENDING",
    },
  });
  // HypothesisとTasksの関連付け
  await prisma.hypothesisTask.create({
    data: {
      hypothesisId: hypothesisAnswer.id,
      taskId: taskForHypothesisAnswer.id,
    },
  });
};

const seedQuestionWhichWardsInTokyoIsMostSchools = async () => {
  // Questionの作成
  const question = await prisma.question.create({
    data: {
      description: "東京都において、学校が最も多い行政区はどこだろう？",
      status: "OPEN",
    },
  });
  // HypothesisWrongの作成
  const hypothesisWrong = await prisma.hypothesis.create({
    data: {
      description: "東京都において、学校が最も多い行政区は渋谷区である。",
      status: "PENDING",
      questionId: question.id, // Questionとの関連付け
    },
  });
  // Taskの作成
  const taskForHypothesisWrong = await prisma.task.create({
    data: {
      description:
        "東京都において、学校が最も多い行政区が渋谷区であることを確認する。",
      status: "PENDING",
    },
  });
  // HypothesisとTasksの関連付け
  await prisma.hypothesisTask.create({
    data: {
      hypothesisId: hypothesisWrong.id,
      taskId: taskForHypothesisWrong.id,
    },
  });
  // HypothesisAnswerの作成
  const hypothesisAnswer = await prisma.hypothesis.create({
    data: {
      description: "東京都において、学校が最も多い行政区は江東区である。",
      status: "PENDING",
      questionId: question.id, // Questionとの関連付け
    },
  });
  // Taskの作成
  const taskForHypothesisAnswer = await prisma.task.create({
    data: {
      description:
        "東京都において、学校が最も多い行政区が江東区であることを確認する。",
      status: "PENDING",
    },
  });
  // HypothesisとTasksの関連付け
  await prisma.hypothesisTask.create({
    data: {
      hypothesisId: hypothesisAnswer.id,
      taskId: taskForHypothesisAnswer.id,
    },
  });
};

// 東京都において、人口あたりの病院の数が最も多い行政区はどこだろう？
const seedQuestionWhichWardsInTokyoIsMostHighestDensityHospitals = async () => {
  // Questionの作成
  const question = await prisma.question.create({
    data: {
      description:
        "東京都において、人口あたりの病院の数が最も多い行政区はどこだろう？",
      status: "OPEN",
    },
  });
  // HypothesisWrongの作成
  const hypothesisWrong = await prisma.hypothesis.create({
    data: {
      description:
        "東京都において、人口あたりの病院の数が最も多い行政区は千代田区である。",
      status: "PENDING",
      questionId: question.id, // Questionとの関連付け
    },
  });
  // Taskの作成
  const taskForHypothesisWrong = await prisma.task.create({
    data: {
      description:
        "東京都において、人口あたりの病院の数が最も多い行政区が千代田区であることを確認する。",
      status: "PENDING",
    },
  });
  // HypothesisとTasksの関連付け
  await prisma.hypothesisTask.create({
    data: {
      hypothesisId: hypothesisWrong.id,
      taskId: taskForHypothesisWrong.id,
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
  await seedQuestionWhichWardsInTokyoIsMostHighestPopulationDensity();
  await seedQuestionWhichWardsInTokyoIsMostHospitals();
  await seedQuestionWhichWardsInTokyoIsMostSchools();
  await seedQuestionWhichWardsInTokyoIsMostHighestDensityHospitals();
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
