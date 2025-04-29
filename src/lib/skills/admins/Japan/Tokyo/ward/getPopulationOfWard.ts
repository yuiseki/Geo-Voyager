import { fetchOverpassData } from "../../../../../common/fetchOverpassData";

/**
 * Fetches the population of a specified ward using Overpass API.
 * @param wardName - The name of the ward to query.
 * @returns The population of the ward.
 */
export async function getPopulationOfWard(wardName: string): Promise<number> {
  const overpassQuery = `
[out:json];
area["name"="東京都"]->.tokyo;
(
  relation["admin_level"="7"]["place"="city"]["name"="${wardName}"](area.tokyo);
);
out tags;
`;
  const response = await fetchOverpassData(overpassQuery);
  let population = 0;
  try {
    population = parseInt(response.elements[0].tags.population);
    if (isNaN(population)) {
      population = 0;
    }
  } catch (error) {
    console.error(`Error fetching population for ${wardName}:`, error);
    population = 0;
  }
  return population;
}
