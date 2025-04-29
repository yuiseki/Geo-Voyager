// description: 東京都において、人口あたりの学校の数が最も多い行政区を探す。
// file_path: src/lib/skills/admins/Japan/Tokyo/findWardWithMostSchoolsPerPopulation.ts

import { getAllWardsInTokyo } from "./ward/getAllWardsInTokyo";
import { getPopulationOfWard } from "./ward/getPopulationOfWard";
import { getSchoolsCountByWard } from "./ward/getSchoolsCountByWard";

/**
 * Calculates the number of schools per population in a specified ward.
 * @param wardName - The name of the ward to query.
 * @returns The number of schools per population.
 */
async function getSchoolsPerPopulationOfWard(
  wardName: string
): Promise<number> {
  const schoolCount = await getSchoolsCountByWard(wardName);
  const population = await getPopulationOfWard(wardName);
  if (population === 0) {
    return 0;
  }
  return population > 0 ? schoolCount / population : 0;
}

export const findWardWithMostSchoolsPerPopulation =
  async (): Promise<string> => {
    const wards = await getAllWardsInTokyo();
    let maxSchoolsPerPopulation = 0;
    let wardWithMostSchoolsPerPopulation = "";
    for (const ward of wards) {
      const schoolsPerPopulation = await getSchoolsPerPopulationOfWard(ward);
      if (schoolsPerPopulation > maxSchoolsPerPopulation) {
        maxSchoolsPerPopulation = schoolsPerPopulation;
        wardWithMostSchoolsPerPopulation = ward;
      }
    }
    return wardWithMostSchoolsPerPopulation;
  };
