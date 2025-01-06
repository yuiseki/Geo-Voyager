import { Hypothesis, PrismaClient } from "@prisma/client";
import fs from "fs";
import path from "path";
import { glob } from "glob";

const prisma = new PrismaClient();

type HypothesisAndTasks = {
  hypothesis: string;
  tasks: string;
};

const dict: {
  question: string;
  hypothesesWrong: HypothesisAndTasks[];
  hypothesesAnswer?: HypothesisAndTasks[];
}[] = [
  {
    question: "世界で最も人口密度が高い国はどこだろう？",
    hypothesesWrong: [
      {
        hypothesis: "世界で最も人口密度が高い国はシンガポールである。",
        tasks: "世界で最も人口密度の高い国がシンガポールであることを確認する。",
      },
    ],
    hypothesesAnswer: [
      {
        hypothesis: "世界で最も人口密度が高い国はマカオである。",
        tasks: "世界で最も人口密度の高い国がマカオであることを確認する。",
      },
    ],
  },
  {
    question: "東京都において、人口密度が最も高い行政区はどこだろう？",
    hypothesesWrong: [
      {
        hypothesis:
          "東京都において、人口密度が最も高い行政区は千代田区である。",
        tasks:
          "東京都において、人口密度が最も高い行政区が千代田区であることを確認する。",
      },
    ],
    hypothesesAnswer: [
      {
        hypothesis: "東京都において、人口密度が最も高い行政区は豊島区である。",
        tasks:
          "東京都において、人口密度が最も高い行政区が豊島区であることを確認する。",
      },
    ],
  },
  {
    question: "東京都において、病院が最も多い行政区はどこだろう？",
    hypothesesWrong: [
      {
        hypothesis: "東京都において、病院が最も多い行政区は江東区である。",
        tasks:
          "東京都において、病院が最も多い行政区が江東区であることを確認する。",
      },
    ],
    hypothesesAnswer: [
      {
        hypothesis: "東京都において、病院が最も多い行政区は多摩市である。",
        tasks:
          "東京都において、病院が最も多い行政区が多摩市であることを確認する。",
      },
    ],
  },
  {
    question: "東京都において、学校が最も多い行政区はどこだろう？",
    hypothesesWrong: [
      {
        hypothesis: "東京都において、学校が最も多い行政区は渋谷区である。",
        tasks:
          "東京都において、学校が最も多い行政区が渋谷区であることを確認する。",
      },
    ],
    hypothesesAnswer: [
      {
        hypothesis: "東京都において、学校が最も多い行政区は江東区である。",
        tasks:
          "東京都において、学校が最も多い行政区が江東区であることを確認する。",
      },
    ],
  },
  {
    question:
      "東京都において、人口あたりの病院の数が最も多い行政区はどこだろう？",
    hypothesesWrong: [
      {
        hypothesis:
          "東京都において、人口あたりの病院の数が最も多い行政区は千代田区である。",
        tasks:
          "東京都において、人口あたりの病院の数が最も多い行政区が千代田区であることを確認する。",
      },
    ],
    hypothesesAnswer: [
      {
        hypothesis:
          "東京都において、人口あたりの病院の数が最も多い行政区は中央区である。",
        tasks:
          "東京都において、人口あたりの病院の数が最も多い行政区が中央区であることを確認する。",
      },
    ],
  },
  {
    question:
      "東京都において、人口あたりの学校の数が最も多い行政区はどこだろう？",
    hypothesesWrong: [
      {
        hypothesis:
          "東京都において、人口あたりの学校の数が最も多い行政区は千代田区である。",
        tasks:
          "東京都において、人口あたりの学校の数が最も多い行政区が千代田区であることを確認する。",
      },
      {
        hypothesis:
          "東京都において、人口あたりの学校の数が最も多い行政区は港区である。",
        tasks:
          "東京都において、人口あたりの学校の数が最も多い行政区が港区であることを確認する。",
      },
    ],
    hypothesesAnswer: [
      {
        hypothesis:
          "東京都において、人口あたりの学校の数が最も多い行政区は中央区である。",
        tasks:
          "東京都において、人口あたりの学校の数が最も多い行政区が中央区であることを確認する。",
      },
    ],
  },
  {
    question:
      "東京都において、人口あたりの公園の数が最も高い行政区はどこだろう？",
    hypothesesWrong: [
      {
        hypothesis:
          "東京都において、人口あたりの公園の数が最も高い行政区は千代田区である。",
        tasks:
          "東京都において、人口あたりの公園の数が最も高い行政区が千代田区であることを確認する。",
      },
    ],
    hypothesesAnswer: [
      {
        hypothesis:
          "東京都において、人口あたりの公園の数が最も高い行政区は稲城市である。",
        tasks:
          "東京都において、人口あたりの公園の数が最も高い行政区が稲城市であることを確認する。",
      },
    ],
  },
  {
    question: "東京都において、面積が最も広い行政区はどこだろう？",
    hypothesesWrong: [
      {
        hypothesis: "東京都において、面積が最も広い行政区は江東区である。",
        tasks:
          "東京都において、面積が最も広い行政区が江東区であることを確認する。",
      },
    ],
    hypothesesAnswer: [
      {
        hypothesis: "東京都において、面積が最も広い行政区は小笠原村である。",
        tasks:
          "東京都において、面積が最も広い行政区が小笠原村であることを確認する。",
      },
    ],
  },
  {
    question:
      "東京都において、人口あたりの図書館の数が最も多い行政区はどこだろう？",
    hypothesesWrong: [
      {
        hypothesis:
          "東京都において、人口あたりの図書館の数が最も多い行政区は千代田区である。",
        tasks:
          "東京都において、人口あたりの図書館の数が最も多い行政区が千代田区であることを確認する。",
      },
    ],
  },
];

/*
世界でGDPが最も高い国はどこだろう？
世界で森林面積の比率が最も高い国はどこだろう？
世界で乳児死亡率（Infant Mortality Rate）が最も低い国はどこだろう？
世界で女性の労働参加率（Female Labor Force Participation Rate）が最も高い国はどこだろう？
世界で農業がGDPに占める割合（農業部門比率）が最も高い国はどこだろう？
世界で都市化率（Urban population % of total population）が最も低い国はどこだろう？
世界で、鉄道網が最も発達している国はどこだろう？
世界の主要都市のなかで、面積あたりのレストラン数が最も多い都市はどこだろう？
世界の主要都市のなかで、自転車用駐輪場の数が最も多い都市はどこだろう？
世界の主要都市のなかで、人口に対する公園の面積が最も高い都市はどこだろう？
世界の主要都市のなかで、公共図書館（libraryタグ等）の数が最も多い都市はどこだろう？
東京都において、公園面積が最も広い行政区はどこだろう？
東京都において、商業施設が最も多い行政区はどこだろう？
東京都において、1人あたりの文化施設が最も多い行政区はどこだろう？
東京都において、交通機関の数が最も多い行政区はどこだろう？
東京都において、高齢者向け施設が最も多い行政区はどこだろう？
東京都において、大学の数が最も多い行政区はどこだろう？
*/

const seedQuestionAndHypothesesWithTasks = async () => {
  for (const { question, hypothesesWrong, hypothesesAnswer } of dict) {
    // Questionの作成
    const questionRecord = await prisma.question.create({
      data: {
        description: question,
        status: "OPEN",
      },
    });

    for (const { hypothesis, tasks } of hypothesesWrong) {
      // HypothesisWrongの作成
      const hypothesisRecord = await prisma.hypothesis.create({
        data: {
          description: hypothesis,
          status: "PENDING",
          questionId: questionRecord.id,
        },
      });

      // Taskの作成
      const taskRecord = await prisma.task.create({
        data: {
          description: tasks,
          status: "PENDING",
        },
      });

      // HypothesisとTasksの関連付け
      await prisma.hypothesisTask.create({
        data: {
          hypothesisId: hypothesisRecord.id,
          taskId: taskRecord.id,
        },
      });
    }

    if (!hypothesesAnswer) {
      continue;
    }
    for (const { hypothesis, tasks } of hypothesesAnswer) {
      // HypothesisAnswerの作成
      const hypothesisRecord = await prisma.hypothesis.create({
        data: {
          description: hypothesis,
          status: "PENDING",
          questionId: questionRecord.id,
        },
      });

      // Taskの作成
      const taskRecord = await prisma.task.create({
        data: {
          description: tasks,
          status: "PENDING",
        },
      });

      // HypothesisとTasksの関連付け
      await prisma.hypothesisTask.create({
        data: {
          hypothesisId: hypothesisRecord.id,
          taskId: taskRecord.id,
        },
      });
    }
  }
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

  await seedQuestionAndHypothesesWithTasks();
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
