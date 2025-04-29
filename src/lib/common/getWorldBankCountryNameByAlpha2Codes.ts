import fs from "fs";

/**
 * Fetches the country name by ISO3166-1 alpha-2 code.
 * @param alpha2Code - The ISO3166-1 alpha-2 country code.
 * @returns The name of the country.
 */
export const getWorldBankCountryNameByAlpha2Codes = async (
  alpha2Code: string
): Promise<string> => {
  let data;
  const cachePath = `./tmp/cache/world_bank/country_name_${alpha2Code}.json`;
  try {
    const cache = await fs.readFileSync(cachePath, "utf-8");
    data = JSON.parse(cache);
  } catch (e) {
    console.debug(
      `Cache not found. Call World Bank API, country, ${alpha2Code}...`
    );
    const endpoint = `https://api.worldbank.org/v2/country/${alpha2Code}?format=json`;
    const res = await fetch(endpoint);
    if (!res.ok) {
      throw new Error(`HTTP error! status: ${res.status}`);
    }
    data = await res.json();
    if (data.length === 0 || !data[1] || data[1].length === 0) {
      throw new Error(`No country data found for country code ${alpha2Code}`);
    }
    // cache the data
    await fs.mkdirSync("./tmp/cache/world_bank", { recursive: true });
    await fs.writeFileSync(cachePath, JSON.stringify(data, null, 2), "utf-8");
  }
  const result = data[1][0].name;
  return result;
};
