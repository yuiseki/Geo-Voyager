// description: 世界のすべての国の ISO3166-1 Alpha-2 コードを取得する
// file_path: src/lib/skills/list/getAllCountriesAlpha2Codes.ts

import fs from "fs";

/**
 * @returns A list of all countries' ISO3166-1 alpha-2 codes.
 */
const getAllCountriesAlpha2Codes = async (): Promise<string> => {
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

export default getAllCountriesAlpha2Codes;
