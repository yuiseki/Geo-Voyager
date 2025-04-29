// description: 東京都において、人口あたりの図書館の数が最も多い行政区を探す。
// file_path: src/lib/skills/admins/Japan/Tokyo/findWardWithMostLibrariesPerPopulation.ts

import { getAllWardsInTokyo } from "./ward/getAllWardsInTokyo";
import { getLibrariesCountByWard } from "./ward/getLibrariesCountByWard";
import { getPopulationOfWard } from "./ward/getPopulationOfWard";

/**
 * Calculates the number of libraries per population in a specified ward.
 * @param wardName - The name of the ward to query.
 * @returns The number of libraries per population of the ward.
 */
async function getLibrariesPerPopulationOfWard(
  wardName: string
): Promise<number> {
  const libraryCount = await getLibrariesCountByWard(wardName);
  const population = await getPopulationOfWard(wardName);
  if (population === 0) {
    return 0;
  }
  return libraryCount / population;
}

const findWardWithMostLibrariesPerPopulation = async (): Promise<string> => {
  const wards = await getAllWardsInTokyo();
  let maxLibrariesPerPopulation = 0;
  let mostLibrariesPerPopulationWard = "";

  for (const ward of wards) {
    if (ward === "") continue; // Skip empty lines
    const librariesPerPopulation = await getLibrariesPerPopulationOfWard(ward);
    if (librariesPerPopulation > maxLibrariesPerPopulation) {
      maxLibrariesPerPopulation = librariesPerPopulation;
      mostLibrariesPerPopulationWard = ward;
    }
  }
  return mostLibrariesPerPopulationWard;
};

export default findWardWithMostLibrariesPerPopulation;
