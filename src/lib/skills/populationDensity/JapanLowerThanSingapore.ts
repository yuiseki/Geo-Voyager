// description: 日本の人口密度がシンガポールよりも低いことを確認する。
// file_path: src/lib/skills/populationDensity/JapanLowerThanSingapore.ts

import * as turf from "@turf/turf";
import osmtogeojson from "osmtogeojson";

/**
 * Fetch data from the Overpass API.
 * @param query - The Overpass QL query string.
 * @returns JSON response from the Overpass API.
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
  return await res.json();
};

/**
 * Fetch total population data from the World Bank API.
 * @param countryCode - The ISO 3166-1 alpha-2 country code.
 * @returns JSON response containing population data.
 */
const fetchWorldBankTotalPopulation = async (
  countryCode: string
): Promise<any> => {
  const endpoint = `https://api.worldbank.org/v2/country/${countryCode}/indicator/SP.POP.TOTL?&format=json`;
  const res = await fetch(endpoint);
  return await res.json();
};

/**
 * Check if Japan's population density is lower than Singapore's.
 * @returns A boolean indicating whether Japan's population density is lower than Singapore's.
 */
const isPopulationDensityOfJapanLowerThanSingapore = async (): Promise<boolean> => {
  // Fetch Singapore's area
  const querySingapore = `[out:json];
relation["name"="Singapore"]["admin_level"=2];
out geom;`;
  const resultSingapore = await fetchOverpassData(querySingapore);
  if (resultSingapore.elements.length === 0) {
    throw new Error(
      `Overpass API returned no data without errors. Please try to fix this query:\n${querySingapore}`
    );
  }
  const geoJsonSingapore = osmtogeojson(resultSingapore);
  if (geoJsonSingapore.features.length === 0) {
    throw new Error(
      `osmtogeojson returned no GeoJSON data. Please try to fix this query:\n${querySingapore}`
    );
  }
  const areaSingapore = turf.area(geoJsonSingapore);

  // Fetch Singapore's population
  const resultPopulationSingapore = await fetchWorldBankTotalPopulation("SG");
  const populationSingapore = resultPopulationSingapore[1][0].value;

  // Calculate Singapore's population density
  const populationDensitySingapore = populationSingapore / areaSingapore;

  // Fetch Japan's area
  const queryJapan = `[out:json];
relation["name:en"="Japan"]["admin_level"=2];
out geom;`;
  const resultJapan = await fetchOverpassData(queryJapan);
  if (resultJapan.elements.length === 0) {
    throw new Error(
      `Overpass API returned no data without errors. Please try to fix this query:\n${queryJapan}`
    );
  }
  const geoJsonJapan = osmtogeojson(resultJapan);
  if (geoJsonJapan.features.length === 0) {
    throw new Error(
      `osmtogeojson returned no GeoJSON data. Please try to fix this query:\n${queryJapan}`
    );
  }
  const areaJapan = turf.area(geoJsonJapan);

  // Fetch Japan's population
  const resultPopulationJapan = await fetchWorldBankTotalPopulation("JP");
  const populationJapan = resultPopulationJapan[1][0].value;

  // Calculate Japan's population density
  const populationDensityJapan = populationJapan / areaJapan;

  return populationDensityJapan < populationDensitySingapore;
};

export default isPopulationDensityOfJapanLowerThanSingapore;