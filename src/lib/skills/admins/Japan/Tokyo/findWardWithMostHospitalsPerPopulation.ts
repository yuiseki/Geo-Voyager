// description: 東京都において、人口あたりの病院の数が最も多い行政区を探す。
// file_path: src/lib/skills/admins/Japan/Tokyo/findWardWithMostHospitalsPerPopulation.ts

import { getHospitalsCountByWard } from "./ward/getHospitalsCountByWard";
import { getPopulationOfWard } from "./ward/getPopulationOfWard";
import { getAllWardsInTokyo } from "./ward/getAllWardsInTokyo";

/**
 * Calculates the number of hospitals per population in a specified ward.
 * @param wardName - The name of the ward to query.
 * @returns The number of hospitals per population of the ward.
 */
async function getHospitalsPerPopulationOfWard(
  wardName: string
): Promise<number> {
  const hospitalCount = await getHospitalsCountByWard(wardName);
  const population = await getPopulationOfWard(wardName);
  if (population === 0) {
    return 0;
  }
  return population > 0 ? hospitalCount / population : 0;
}

export const findWardWithMostHospitalsPerPopulation =
  async (): Promise<string> => {
    const wards = await getAllWardsInTokyo();
    let maxHospitalsPerPopulation = 0;
    let mostHospitalsPerPopulationWard = "";
    for (const ward of wards) {
      const hospitalsPerPopulation = await getHospitalsPerPopulationOfWard(
        ward
      );
      if (hospitalsPerPopulation > maxHospitalsPerPopulation) {
        maxHospitalsPerPopulation = hospitalsPerPopulation;
        mostHospitalsPerPopulationWard = ward;
      }
    }
    return mostHospitalsPerPopulationWard;
  };
