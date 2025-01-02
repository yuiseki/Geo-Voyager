import { PrismaClient } from "@prisma/client";

const prisma = new PrismaClient();

async function main() {
  await prisma.hypothesis.createMany({
    data: [
      {
        description:
          "東京都においては、人口密度が高い行政区ほど、1人当たりの公園面積が小さい。",
        status: "PENDING",
      },
      {
        description:
          "東京都においては、鉄道路線の数が多い行政区ほど、駅の密度も高い。",
        status: "PENDING",
      },
      {
        description:
          "東京都においては、行政区の面積が広いほど、学校の数が多い。",
        status: "PENDING",
      },
      {
        description:
          "東京都においては、行政区の面積が広いほど、病院の数が多い。",
        status: "PENDING",
      },
      {
        description:
          "東京都においては、行政区の面積が広いほど、図書館の数が多い。",
        status: "PENDING",
      },
      {
        description:
          "東京都においては、行政区の面積が広いほど、公園の数が多い。",
        status: "PENDING",
      },
      {
        description:
          "東京都においては、商業施設の多い行政区ほど、駐車場の数が多い。",
        status: "PENDING",
      },
      {
        description:
          "東京都においては、駅の密度が高い行政区ほど、自転車駐輪場が多い。",
        status: "PENDING",
      },
      {
        description:
          "東京都においては、駅の密度が高い行政区ほど、商業施設が多い。",
        status: "PENDING",
      },
    ],
  });

  console.log("Bootstrap hypotheses seeded.");
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
