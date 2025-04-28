// description: 東京都において、面積が最も広い行政区を探す。
// file_path: src/lib/skills/admins/Japan/Tokyo/findLargestWard.ts

import { getAllWardsInTokyo } from "./ward/getAllWardsInTokyo";
import { getAreaOfWard } from "./ward/getAreaOfWard";

export const findLargestWard = async (): Promise<string> => {
  const wards = await getAllWardsInTokyo();
  let maxArea = 0;
  let wardWithLargestArea = "";
  for (const ward of wards) {
    const area = await getAreaOfWard(ward);
    if (area > maxArea) {
      maxArea = area;
      wardWithLargestArea = ward;
    }
  }
  return wardWithLargestArea;
};
