// description: シンガポールの人口密度がバーレーンよりも高いことを確認する。
// file_path: src/lib/skills/populationDensity/SingaporeHigherThanBahrain.ts
import * as turf from "@turf/turf";
import osmtogeojson from "osmtogeojson";

/**
 * @returns boolean
 */
const isPopulationDensityOfSingaporeHigherThanBahrain = async () => {
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
  const areaSingapore = turf.area(geoJsonSingapore);
  // シンガポールの人口を取得
  const resultPopulationSingapore = await fetchWorldBankTotalPopulation("sg");
  const populationSingapore = resultPopulationSingapore[1][0].value;
  // シンガポールの人口密度を計算
  const populationDensitySingapore = populationSingapore / areaSingapore;

  // バーレーンの面積を取得
  const queryBahrain = `[out:json];
relation["name:en"="Bahrain"]["admin_level"=2];
out geom;`;
  const resultBahrain = await fetchOverpassData(queryBahrain);
  if (resultBahrain.elements.length === 0) {
    throw new Error(
      `Overpass API returned no data without errors. Please try to fix this query:\n${queryBahrain}`
    );
  }
  const geoJsonBahrain = osmtogeojson(resultBahrain);
  if (geoJsonBahrain.features.length === 0) {
    throw new Error(
      `osmtogeojson returned no GeoJSON data. Please try to fix this query:\n${queryBahrain}`
    );
  }
  const areaBahrain = turf.area(geoJsonBahrain);
  // バーレーンの人口を取得
  const resultBahrainPopulation = await fetchWorldBankTotalPopulation("bh");
  const populationBahrain = resultBahrainPopulation[1][0].value;
  // バーレーンの人口密度を計算
  const populationDensityBahrain = populationBahrain / areaBahrain;

  return populationDensitySingapore > populationDensityBahrain;
};

export default isPopulationDensityOfSingaporeHigherThanBahrain;
