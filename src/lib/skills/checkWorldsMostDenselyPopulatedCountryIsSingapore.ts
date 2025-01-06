// description: 世界で最も人口密度の高い国がシンガポールであることを確認する。
// file_path: src/lib/skills/checkWorldsMostDenselyPopulatedCountryIsSingapore.ts

import fs from "fs";

/**
 * Fetches population density data from the World Bank API.
 * @param countryCode - The ISO 3166-1 alpha-2 country code.
 * @returns Promise resolving to JSON data containing the population density.
 */
const fetchWorldBankPopulationDensity = async (
  countryCode: string
): Promise<any> => {
  const cachePath = `./tmp/cache/world_bank/population_density_${countryCode}.json`;
  try {
    const cache = await fs.readFileSync(cachePath, "utf-8");
    return JSON.parse(cache);
  } catch (e) {
    console.debug("Cache not found. Call World Bank API...");
  }
  const endpoint = `https://api.worldbank.org/v2/country/${countryCode}/indicator/EN.POP.DNST?format=json`;
  const res = await fetch(endpoint);
  if (!res.ok) {
    throw new Error(`HTTP error! status: ${res.status}`);
  }
  const data = await res.json();
  // cache the data
  await fs.mkdirSync("./tmp/cache/world_bank", { recursive: true });
  await fs.writeFileSync(cachePath, JSON.stringify(data, null, 2), "utf-8");
  if (data.length === 0 || !data[1] || data[1].length === 0) {
    throw new Error(
      `No population density data found for country code ${countryCode}`
    );
  }
  const rows = data[1];
  const value = rows.filter(
    (row: any) => row.value !== null && row.value !== 0
  )[0].value;
  return value;
};

/**
 * @returns A list of all countries' ISO3166-1 alpha-2 codes.
 */
const fetchAllCountriesAlpha2Codes = async (): Promise<string> => {
  const cachePath = "./tmp/cache/world_bank/countries_alpha2_codes.json";
  try {
    const cache = await fs.readFileSync(cachePath, "utf-8");
    return JSON.parse(cache).join("\n");
  } catch (e) {
    console.debug("Cache not found. Call World Bank API...");
  }
  let page = 1;
  let pages = 100;
  let result = [];
  while (page <= pages) {
    const endpoint = `https://api.worldbank.org/v2/country?format=json&page=${page}`;
    const res = await fetch(endpoint);
    if (!res.ok) {
      throw new Error(`HTTP error! status: ${res.status}`);
    }
    const data = await res.json();
    if (page === 1) {
      pages = data[0].pages;
    }
    const countries = data[1];
    for (const country of countries) {
      if (country.longitude.length === 0 || country.latitude.length === 0) {
        continue;
      }
      result.push(country.iso2Code);
    }
    page++;
  }
  // cache the data
  await fs.mkdirSync("./tmp/cache/world_bank", { recursive: true });
  await fs.writeFileSync(cachePath, JSON.stringify(result, null, 2), "utf-8");
  return result.join("\n");
};

/**
 * Fetches the country name by ISO3166-1 alpha-2 code.
 * @param alpha2Code - The ISO3166-1 alpha-2 country code.
 * @returns The name of the country.
 */
const getCountryNameByAlpha2Codes = async (
  alpha2Code: string
): Promise<string> => {
  const cachePath = `./tmp/cache/world_bank/country_name_${alpha2Code}.json`;
  try {
    const cache = await fs.readFileSync(cachePath, "utf-8");
    return JSON.parse(cache)[1][0].name;
  } catch (e) {
    console.debug("Cache not found. Call World Bank API...");
  }
  const endpoint = `https://api.worldbank.org/v2/country/${alpha2Code}?format=json`;
  const res = await fetch(endpoint);
  if (!res.ok) {
    throw new Error(`HTTP error! status: ${res.status}`);
  }
  const data = await res.json();
  if (data.length === 0 || !data[1] || data[1].length === 0) {
    throw new Error(`No country data found for country code ${alpha2Code}`);
  }
  // cache the data
  await fs.mkdirSync("./tmp/cache/world_bank", { recursive: true });
  await fs.writeFileSync(cachePath, JSON.stringify(data, null, 2), "utf-8");
  return data[1][0].name;
};

/**
 * @returns The ISO3166-1 alpha-2 country code of the most densely populated country.
 */
const getWorldsMostDenselyPopulatedCountry = async (): Promise<string> => {
  const alpha2Codes = await fetchAllCountriesAlpha2Codes();
  let mostDenselyPopulatedCountry = "";
  let highestPopulationDensity = 0;
  for (const code of alpha2Codes.split("\n")) {
    try {
      const populationDensity = await fetchWorldBankPopulationDensity(code);
      console.log(
        `getMostDenselyPopulatedCountry, ${code}: ${populationDensity}`
      );
      if (populationDensity > highestPopulationDensity) {
        highestPopulationDensity = populationDensity;
        mostDenselyPopulatedCountry = await getCountryNameByAlpha2Codes(code);
      }
    } catch (error) {
      console.error(`getMostDenselyPopulatedCountry, ${code}: ${error}`);
      continue;
    }
  }
  return mostDenselyPopulatedCountry;
};

const checkWorldsMostDenselyPopulatedCountryIsSingapore =
  async (): Promise<boolean> => {
    const mostDenselyPopulatedCountry =
      await getWorldsMostDenselyPopulatedCountry();
    return mostDenselyPopulatedCountry.includes("Singapore");
  };

export default checkWorldsMostDenselyPopulatedCountryIsSingapore;
