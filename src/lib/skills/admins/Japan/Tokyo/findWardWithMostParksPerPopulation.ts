// description: 東京都において、人口あたりの公園の数が最も高い行政区を探す。
// file_path: src/lib/skills/admins/Japan/Tokyo/findWardWithMostParksPerPopulation.ts

import { getAllWardsInTokyo } from "./ward/getAllWardsInTokyo";
import { getParkCountByWard } from "./ward/getParkCountByWard";
import { getPopulationOfWard } from "./ward/getPopulationOfWard";

/**
 * Calculates the number of parks per population in a specified ward.
 * @param wardName - The name of the ward to query.
 * @returns The number of parks per population of the ward.
 */
async function getParksPerPopulationOfWard(wardName: string): Promise<number> {
  const parkCount = await getParkCountByWard(wardName);
  const population = await getPopulationOfWard(wardName);
  if (population === 0) {
    return 0;
  }
  return population > 0 ? parkCount / population : 0;
}

export const findWardWithMostParksPerPopulation = async (): Promise<string> => {
  const wards = await getAllWardsInTokyo();
  let maxParksPerPopulation = 0;
  let mostPerksPerPopulationWard = "";
  for (const ward of wards) {
    const parksPerPopulation = await getParksPerPopulationOfWard(ward);
    if (parksPerPopulation > maxParksPerPopulation) {
      maxParksPerPopulation = parksPerPopulation;
      mostPerksPerPopulationWard = ward;
    }
  }
  return mostPerksPerPopulationWard;
};
