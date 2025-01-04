// description: シンガポールの人口密度がタイよりも高いことを確認する。
// file_path: src/lib/skills/populationDensity/SingaporeHigherThanThailand.ts
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
  return res.json();
};

/**
 * Fetches total population data from the World Bank API.
 * @param countryCode - The ISO 3166-1 alpha-2 country code.
 * @returns Promise resolving to JSON data containing the population.
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
 * Checks if Singapore's population density is higher than Thailand's.
 * @returns Promise resolving to a boolean indicating the result.
 */
const isSingaporePopulationDensityHigherThanThailand =
  async (): Promise<boolean> => {
    try {
      // Fetch Singapore's geojson data
      const singaporeQuery = `[out:json];relation["name:en"="Singapore"]["admin_level"=2];out geom;>;`;
      const singaporeData = await fetchOverpassData(singaporeQuery);
      const singaporeGeojsonData = osmtogeojson(singaporeData);

      // Fetch Thailand's geojson data
      const thailandQuery = `[out:json];relation["name:en"="Thailand"]["admin_level"=2];out geom;`;
      const thailandData = await fetchOverpassData(thailandQuery);
      const thailandGeojsonData = osmtogeojson(thailandData);

      // Fetch population data
      const singaporePopulation = await fetchWorldBankPopulation("SG");
      const thailandPopulation = await fetchWorldBankPopulation("TH");

      // Calculate population densities
      const singaporeDensity = calculatePopulationDensity(
        singaporeGeojsonData,
        singaporePopulation[1][0].value
      );
      const thailandDensity = calculatePopulationDensity(
        thailandGeojsonData,
        thailandPopulation[1][0].value
      );

      return singaporeDensity > thailandDensity;
    } catch (error) {
      console.error(`Error calculating population density: ${error}`);
      return false;
    }
  };

export default isSingaporePopulationDensityHigherThanThailand;
