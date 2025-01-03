// description: シンガポールの人口密度がモナコよりも低いことを確認する。
// file_path: src/lib/skills/populationDensity/SingaporeLowerThanMonaco.ts

import * as turf from "@turf/turf";
import osmtogeojson from "osmtogeojson";

/**
 * @returns {boolean} - True if the population density of Singapore is lower than Monaco, otherwise false.
 */
const isPopulationDensityOfSingaporeLowerThanMonaco = async () => {
  /**
   *
   * @param query Overpass QL
   * @returns Overpass API JSON
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
   *
   * @param countryCode ISO 3166-1 alpha-2 country code
   * @returns JSON
   */
  const fetchWorldBankTotalPopulation = async (
    countryCode: string
  ): Promise<any> => {
    const endpoint = `https://api.worldbank.org/v2/country/${countryCode}/indicator/SP.POP.TOTL?&format=json`;
    const res = await fetch(endpoint);
    return await res.json();
  };

  // シンガポールの面積を取得
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
  const areaSingapore = turf.area(geoJsonSingapore.features[0]);
  // シンガポールの人口を取得
  const resultPopulationSingapore = await fetchWorldBankTotalPopulation("sg");
  const populationSingapore = resultPopulationSingapore[1][0].value;
  // シンガポールの人口密度を計算
  const populationDensitySingapore = populationSingapore / areaSingapore;

  // モナコの面積を取得
  const queryMonaco = `[out:json];
relation["name"="Monaco"]["admin_level"=2];
out geom;`;
  const resultMonaco = await fetchOverpassData(queryMonaco);
  if (resultMonaco.elements.length === 0) {
    throw new Error(
      `Overpass API returned no data without errors. Please try to fix this query:\n${queryMonaco}`
    );
  }
  const geoJsonMonaco = osmtogeojson(resultMonaco);
  if (geoJsonMonaco.features.length === 0) {
    throw new Error(
      `osmtogeojson returned no GeoJSON data. Please try to fix this query:\n${queryMonaco}`
    );
  }
  const areaMonaco = turf.area(geoJsonMonaco.features[0]);
  // モナコの人口を取得
  const resultPopulationMonaco = await fetchWorldBankTotalPopulation("mc");
  const populationMonaco = resultPopulationMonaco[1][0].value;
  // モナコの人口密度を計算
  const populationDensityMonaco = populationMonaco / areaMonaco;

  return populationDensitySingapore < populationDensityMonaco;
};

export default isPopulationDensityOfSingaporeLowerThanMonaco;