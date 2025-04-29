// description: 世界で人口密度が最も高い国を探す。
// file_path: src/lib/skills/checkSingaporeIsMostDenselyPopulatedCountryInWorld.ts

import { getWorldBankAllCountriesAlpha2Codes } from "../../common/getWorldBankAllCountriesAlpha2Codes";
import { getWorldBankCountryNameByAlpha2Codes } from "../../common/getWorldBankCountryNameByAlpha2Codes";
import { getWorldBankPopulationDensityByCountryCode } from "../../common/getWorldBankPopulationDensityByCountryCode";

/**
 * @returns The ISO3166-1 alpha-2 country code of the most densely populated country.
 */
const getWorldsMostDenselyPopulatedCountry = async (): Promise<string> => {
  const alpha2Codes = await getWorldBankAllCountriesAlpha2Codes();
  let mostDenselyPopulatedCountry = "";
  let highestPopulationDensity = 0;
  for (const code of alpha2Codes) {
    // codeがstring型でない場合はスキップ
    if (typeof code !== "string") {
      continue;
    }
    if (code === "XK") {
      // Kosovo has no population density data at the World Bank API
      continue;
    }
    try {
      const populationDensity =
        await getWorldBankPopulationDensityByCountryCode(code);
      if (populationDensity > highestPopulationDensity) {
        highestPopulationDensity = populationDensity;
        mostDenselyPopulatedCountry =
          await getWorldBankCountryNameByAlpha2Codes(code);
      }
    } catch (error) {
      console.error(`getMostDenselyPopulatedCountry, ${code}: ${error}`);
      continue;
    }
  }
  return mostDenselyPopulatedCountry;
};

export const findMostDenselyPopulatedCountry = async (): Promise<string> => {
  const mostDenselyPopulatedCountry =
    await getWorldsMostDenselyPopulatedCountry();
  return mostDenselyPopulatedCountry;
};
