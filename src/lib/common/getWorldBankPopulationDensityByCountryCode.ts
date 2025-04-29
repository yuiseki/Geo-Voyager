import fs from "fs";

/**
 * Fetches population density data from the World Bank API.
 * @param countryCode - The ISO 3166-1 alpha-2 country code.
 * @returns Promise resolving to JSON data containing the population density.
 */
export const getWorldBankPopulationDensityByCountryCode = async (
  countryCode: string
): Promise<any> => {
  let data;
  const cachePath = `./tmp/cache/world_bank/population_density_${countryCode}.json`;
  try {
    const cache = await fs.readFileSync(cachePath, "utf-8");
    data = JSON.parse(cache);
  } catch (e) {
    console.debug(
      `Cache not found. Call World Bank API, country, ${countryCode}, EN.POP.DNST,...`
    );
    const endpoint = `https://api.worldbank.org/v2/country/${countryCode}/indicator/EN.POP.DNST?format=json`;
    const res = await fetch(endpoint);
    if (!res.ok) {
      throw new Error(`HTTP error! status: ${res.status}`);
    }
    data = await res.json();
    // cache the data
    await fs.mkdirSync("./tmp/cache/world_bank", { recursive: true });
    await fs.writeFileSync(cachePath, JSON.stringify(data, null, 2), "utf-8");
    if (data.length === 0 || !data[1] || data[1].length === 0) {
      throw new Error(
        `No population density data found for country code ${countryCode}`
      );
    }
  }

  const rows = data[1];
  const value = rows.filter(
    (row: any) => row.value !== null && row.value !== 0
  )[0].value;
  return value;
};
