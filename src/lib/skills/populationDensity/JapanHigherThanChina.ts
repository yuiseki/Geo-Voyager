// description: 日本の人口密度が中国よりも高いことを確認する。
// file_path: src/lib/skills/populationDensity/JapanHigherThanChina.ts

import * as turf from "@turf/turf";
import osmtogeojson from "osmtogeojson";

/**
 * Fetches data from the Overpass API.
 * @param query - The Overpass QL query string.
 * @returns Promise resolving to JSON data from the Overpass API.
 */
const fetchOverpassData = async (query: string): Promise<any> => {
  const endpoint = "https://overpass-api.de/api/interpreter";
  const res = await fetch(endpoint, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: `data=${encodeURIComponent(query)}`,
  });
  if (!res.ok) {
    throw new Error(`HTTP error! status: ${res.status}`);
  }
  const data = await res.json();
  if (!data.elements || data.elements.length === 0) {
    throw new Error(
      `Overpass API returned no data without errors. Please try to fix this query:\n${query}`
    );
  }
  return data;
};

/**
 * Fetches total population data from the World Bank API.
 * @param countryCode - The ISO 3166-1 alpha-2 country code.
 * @returns Promise resolving to JSON data containing the population.
 */
const fetchWorldBankTotalPopulation = async (
  countryCode: string
): Promise<any> => {
  const endpoint = `https://api.worldbank.org/v2/country/${countryCode}/indicator/SP.POP.TOTL?format=json`;
  const res = await fetch(endpoint);
  if (!res.ok) {
    throw new Error(`HTTP error! status: ${res.status}`);
  }
  const data = await res.json();
  if (data.length === 0 || data[1].length === 0) {
    throw new Error(`No population data found for country code ${countryCode}`);
  }
  return data;
};

/**
 * Calculates the population density of a country.
 * @param geojsonData - GeoJSON data representing the country's boundaries.
 * @param population - The total population of the country.
 * @returns Population density in people per square kilometer.
 */
const calculatePopulationDensity = (
  geojsonData: any,
  population: number
): number => {
  const area = turf.area(geojsonData); // Area in square meters
  const areaInKm2 = area / 1000000; // Convert to square kilometers
  return population / areaInKm2;
};

/**
 * @return boolean
 */
const isPopulationDensityOfJapanHigherThanChina =
  async (): Promise<boolean> => {
    // Fetch Japan's geojson data
    const japanOverpassQuery = `[out:json];relation["name:en"="Japan"]["admin_level"=2];out geom;`;
    const japanOverpassData = await fetchOverpassData(japanOverpassQuery);
    const japanGeojsonData = osmtogeojson(japanOverpassData);
    // Fetch Japan's population
    const japanPopulationData = await fetchWorldBankTotalPopulation("jp");
    const japanPopulation = japanPopulationData[1][0].value;
    // Calculate Japan's population density
    const japanPopulationDensity = calculatePopulationDensity(
      japanGeojsonData,
      japanPopulation
    );

    // Fetch China's geojson data
    const chinaOverpassQuery = `[out:json];relation["name:en"="China"]["admin_level"=2];out geom;`;
    const chinaOverpassData = await fetchOverpassData(chinaOverpassQuery);
    const chinaGeojsonData = osmtogeojson(chinaOverpassData);
    // Fetch China's population
    const chinaPopulationData = await fetchWorldBankTotalPopulation("cn");
    const chinaPopulation = chinaPopulationData[1][0].value;
    // Calculate China's population density
    const chinaPopulationDensity = calculatePopulationDensity(
      chinaGeojsonData,
      chinaPopulation
    );

    // Compare the population densities
    return japanPopulationDensity > chinaPopulationDensity;
  };

export default isPopulationDensityOfJapanHigherThanChina;
