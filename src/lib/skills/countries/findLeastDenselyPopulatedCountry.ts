// filepath: /home/yuiseki/src/github.com/yuiseki/Geo-Voyager/src/lib/skills/findLeastDenselyPopulatedCountry.ts
// description: 世界で人口密度が最も低い国を探す。

import { getWorldBankAllCountriesAlpha2Codes } from "../../common/getWorldBankAllCountriesAlpha2Codes";
import { getWorldBankCountryNameByAlpha2Codes } from "../../common/getWorldBankCountryNameByAlpha2Codes";
import { getWorldBankPopulationDensityByCountryCode } from "../../common/getWorldBankPopulationDensityByCountryCode";

/**
 * @returns The name of the least densely populated country.
 */
const getWorldsLeastDenselyPopulatedCountry = async (): Promise<string> => {
  const alpha2Codes = await getWorldBankAllCountriesAlpha2Codes();
  let leastDenselyPopulatedCountry = "";
  let lowestPopulationDensity = Number.MAX_VALUE;

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
      // 人口密度が0または非常に小さい値の場合は、無人島や特殊な地域の可能性があるのでスキップ
      if (populationDensity <= 0) {
        continue;
      }
      if (populationDensity < lowestPopulationDensity) {
        lowestPopulationDensity = populationDensity;
        leastDenselyPopulatedCountry =
          await getWorldBankCountryNameByAlpha2Codes(code);
      }
    } catch (error) {
      console.error(`getWorldsLeastDenselyPopulatedCountry, ${code}: ${error}`);
      continue;
    }
  }
  return leastDenselyPopulatedCountry;
};

export const findLeastDenselyPopulatedCountry = async (): Promise<string> => {
  const leastDenselyPopulatedCountry =
    await getWorldsLeastDenselyPopulatedCountry();
  return leastDenselyPopulatedCountry;
};
