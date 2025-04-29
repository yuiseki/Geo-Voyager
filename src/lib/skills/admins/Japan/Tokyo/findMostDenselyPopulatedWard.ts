// description: 東京都において、人口密度が最も高い行政区を探す。
// file_path: src/lib/skills/admins/Japan/Tokyo/findMostDenselyPopulatedWard.ts

import { getPopulationOfWard } from "./ward/getPopulationOfWard";
import { getAreaOfWard } from "./ward/getAreaOfWard";
import { getAllWardsInTokyo } from "./ward/getAllWardsInTokyo";

/**
 * Get the population density of a ward in Tokyo.
 * @param wardName - The name of the ward to calculate the population density.
 * @returns The population density of the ward.
 */
async function getPopulationDensityOfWards(wardName: string): Promise<number> {
  const population = await getPopulationOfWard(wardName);
  const areaKm2 = await getAreaOfWard(wardName);
  if (areaKm2 === 0) {
    return 0;
  }
  return population / areaKm2;
}

export const findMostDenselyPopulatedWard = async (): Promise<string> => {
  const wards = await getAllWardsInTokyo();
  let maxPopulationDensity = 0;
  let mostDenselyPopulatedWard = "";
  for (const ward of wards) {
    const populationDensity = await getPopulationDensityOfWards(ward);
    if (populationDensity > maxPopulationDensity) {
      maxPopulationDensity = populationDensity;
      mostDenselyPopulatedWard = ward;
    }
  }
  return mostDenselyPopulatedWard;
};
