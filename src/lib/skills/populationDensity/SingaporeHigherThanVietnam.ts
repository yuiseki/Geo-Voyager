// description: シンガポールの人口密度がベトナムよりも高いことを確認する。
// file_path: src/lib/skills/populationDensity/SingaporeHigherThanVietnam.ts

import * as turf from "@turf/turf";
import osmtogeojson from "osmtogeojson";

/**
 * Fetches data from the Overpass API.
 * @param query - The Overpass QL query to execute.
 * @returns Promise resolving to the JSON response from the Overpass API.
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
  return res.json();
};

/**
 * Fetches the total population for a given country code from the World Bank API.
 * @param countryCode - The ISO 3166-1 alpha-2 country code.
 * @returns Promise resolving to the population value.
 */
const fetchWorldBankPopulation = async (
  countryCode: string
): Promise<number> => {
  const endpoint = `https://api.worldbank.org/v2/country/${countryCode}/indicator/SP.POP.TOTL?format=json`;
  const res = await fetch(endpoint);
  const data = await res.json();
  return data[1][0].value;
};

/**
 * Calculates the population density of a country.
 * @param area - The area in square meters.
 * @param population - The total population.
 * @returns Population density in people per square kilometer.
 */
const calculatePopulationDensity = (
  area: number,
  population: number
): number => {
  return (population / area) * 1e6; // Convert from m² to km²
};

/**
 * Checks if Singapore's population density is higher than Vietnam's.
 * @returns Promise resolving to a boolean indicating the result.
 */
const isPopulationDensityOfSingaporeHigherThanVietnam =
  async (): Promise<boolean> => {
    try {
      // Fetch Singapore's area and population
      const querySingapore = `[out:json];
relation["name"="Singapore"]["admin_level"=2];
out geom;`;
      const dataSingapore = await fetchOverpassData(querySingapore);
      const geoJsonSingapore = osmtogeojson(dataSingapore);
      const areaSingapore = turf.area(geoJsonSingapore);
      const populationSingapore = await fetchWorldBankPopulation("SG");

      // Fetch Vietnam's area and population
      const queryVietnam = `[out:json];
relation["name:en"="Vietnam"]["admin_level"=2];
out geom;`;
      const dataVietnam = await fetchOverpassData(queryVietnam);
      const geoJsonVietnam = osmtogeojson(dataVietnam);
      const areaVietnam = turf.area(geoJsonVietnam);
      const populationVietnam = await fetchWorldBankPopulation("VN");

      // Calculate population densities
      const densitySingapore = calculatePopulationDensity(
        areaSingapore,
        populationSingapore
      );
      const densityVietnam = calculatePopulationDensity(
        areaVietnam,
        populationVietnam
      );

      return densitySingapore > densityVietnam;
    } catch (error) {
      console.error("Error fetching data:", error);
      throw new Error("Failed to determine population densities.");
    }
  };

export default isPopulationDensityOfSingaporeHigherThanVietnam;
