// filepath: /home/yuiseki/src/github.com/yuiseki/Geo-Voyager/src/lib/common/getWorldBankAreaByCountryCode.ts
import { getWorldBankPopulationByCountryCode } from "./getWorldBankPopulationByCountryCode";
import { getWorldBankPopulationDensityByCountryCode } from "./getWorldBankPopulationDensityByCountryCode";

/**
 * Calculates the land area of a country from its population and population density.
 * @param countryCode - The ISO 3166-1 alpha-2 country code.
 * @returns Promise resolving to the land area of the country in square kilometers.
 */
export const getWorldBankAreaByCountryCode = async (
  countryCode: string
): Promise<number> => {
  // 人口密度（人/km²）
  const populationDensity = await getWorldBankPopulationDensityByCountryCode(
    countryCode
  );

  // 人口（人）
  const population = await getWorldBankPopulationByCountryCode(countryCode);

  // 面積（km²）= 人口（人）÷ 人口密度（人/km²）
  const area = population / populationDensity;

  return area;
};
