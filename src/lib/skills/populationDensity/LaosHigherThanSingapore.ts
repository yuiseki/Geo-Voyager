// description: ラオスの人口密度がシンガポールよりも高いことを確認する。
// file_path: src/lib/skills/populationDensity/LaosHigherThanSingapore.ts

import * as turf from "@turf/turf";
import osmtogeojson from "osmtogeojson";

/**
 * Fetches data from the Overpass API.
 * @param query - The Overpass QL query string.
 * @returns Promise resolving to the JSON response from the Overpass API.
 */
const fetchOverpassData = async (query: string): Promise<any> => {
  const endpoint = "https://overpass-api.de/api/interpreter";
  const res = await fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: `data=${encodeURIComponent(query)}`,
  });
  if (!res.ok) {
    throw new Error(`HTTP error! status: ${res.status}`);
  }
  return res.json();
};

/**
 * Fetches population data from the World Bank API.
 * @param countryCode - The ISO 3166-1 alpha-2 country code.
 * @returns Promise resolving to the JSON response containing population data.
 */
const fetchWorldBankPopulation = async (countryCode: string): Promise<any> => {
  const endpoint = `https://api.worldbank.org/v2/country/${countryCode}/indicator/SP.POP.TOTL?format=json`;
  const res = await fetch(endpoint);
  if (!res.ok) {
    throw new Error(`HTTP error! status: ${res.status}`);
  }
  return res.json();
};

/**
 * Calculates the population density of a country.
 * @param geojsonData - The GeoJSON data representing the country's boundaries.
 * @param population - The total population of the country.
 * @returns The population density in people per square kilometer.
 */
const calculatePopulationDensity = (
  geojsonData: any,
  population: number
): number => {
  const area = turf.area(geojsonData);
  return population / area;
};

/**
 * Checks if Laos's population density is higher than Singapore's.
 * @returns Promise resolving to a boolean indicating whether Laos's population density is higher.
 */
const isLaosPopulationDensityHigherThanSingapore =
  async (): Promise<boolean> => {
    try {
      // Fetch Laos's GeoJSON data
      const laosQuery = `[out:json];
relation["name:en"="Laos"]["admin_level"=2];
out geom;`;
      const laosData = await fetchOverpassData(laosQuery);
      const laosGeojsonData = osmtogeojson(laosData);

      // Fetch Laos's population data
      const laosPopulationData = await fetchWorldBankPopulation("LA");
      const laosPopulation = laosPopulationData[1][0].value;

      // Calculate Laos's population density
      const laosPopulationDensity = calculatePopulationDensity(
        laosGeojsonData,
        laosPopulation
      );

      // Fetch Singapore's GeoJSON data
      const singaporeQuery = `[out:json];
relation["name"="Singapore"]["admin_level"=2];
out geom;`;
      const singaporeData = await fetchOverpassData(singaporeQuery);
      const singaporeGeojsonData = osmtogeojson(singaporeData);

      // Fetch Singapore's population data
      const singaporePopulationData = await fetchWorldBankPopulation("SG");
      const singaporePopulation = singaporePopulationData[1][0].value;

      // Calculate Singapore's population density
      const singaporePopulationDensity = calculatePopulationDensity(
        singaporeGeojsonData,
        singaporePopulation
      );

      // Compare the population densities
      return laosPopulationDensity > singaporePopulationDensity;
    } catch (error) {
      console.error("Error fetching data:", error);
      throw error;
    }
  };

export default isLaosPopulationDensityHigherThanSingapore;
