import { prisma } from ".";

export enum HypothesisStatus {
  PENDING = "PENDING", // 検証中
  VERIFIED = "VERIFIED", // 仮説が支持された（洞察と見なされる）
  REJECTED = "REJECTED", // 仮説が棄却された
  UNVERIFIABLE_FETCH = "UNVERIFIABLE_FETCH", // データ収集の失敗
  UNVERIFIABLE_ANALYZE = "UNVERIFIABLE_ANALYZE", // データ分析の失敗
}

// 仮説を作成する関数
export const createHypothesis = async (description: string) => {
  return await prisma.hypothesis.create({
    data: {
      description,
    },
  });
};

// 仮説のステータスを更新する関数
export const updateHypothesisStatus = async (
  id: number,
  status: HypothesisStatus
) => {
  return await prisma.hypothesis.update({
    where: { id },
    data: { status },
  });
};

// 特定のIDの仮説を取得する関数
export const getHypothesisById = async (id: number) => {
  return await prisma.hypothesis.findUnique({
    where: { id },
  });
};

// すべての仮説を取得する関数
export const getHypotheses = async () => {
  return await prisma.hypothesis.findMany();
};

// 特定のステータスの仮説を取得する関数
export const getHypothesesByStatus = async (status: HypothesisStatus) => {
  return await prisma.hypothesis.findMany({
    where: {
      status,
    },
  });
};

// 特定のステータスの仮説の最新一件を取得する関数
export const getLatestHypothesisByStatus = async (status: HypothesisStatus) => {
  return await prisma.hypothesis.findFirst({
    where: {
      status,
    },
    orderBy: {
      createdAt: "desc",
    },
  });
};
