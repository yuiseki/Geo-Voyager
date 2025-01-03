// description: シンガポールの人口密度が中国よりも高いことを確認する。
// file_path: src/lib/skills/populationDensity/SingaporeHigherThanChina.ts
import * as turf from "@turf/turf";
import osmtogeojson from "osmtogeojson";

/**
 * @return boolean
 */
const isPopulationDensityOfSingaporeHigherThanChina = async () => {
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

  // 中国の面積を取得
  const queryChina = `[out:json];
relation["name:en"="China"]["admin_level"=2];
out geom;`;
  const resultChina = await fetchOverpassData(queryChina);
  if (resultChina.elements.length === 0) {
    throw new Error(
      `Overpass API returned no data without errors. Please try to fix this query:\n${queryChina}`
    );
  }
  const geoJsonChina = osmtogeojson(resultChina);
  if (geoJsonChina.features.length === 0) {
    throw new Error(
      `osmtogeojson returned no GeoJSON data. Please try to fix this query:\n${queryChina}`
    );
  }
  const areaChina = turf.area(geoJsonChina);
  // 中国の人口を取得
  const resultChinaPopulation = await fetchWorldBankTotalPopulation("cn");
  const populationChina = resultChinaPopulation[1][0].value;
  // 中国の人口密度を計算
  const populationDensityChina = populationChina / areaChina;

  return populationDensitySingapore > populationDensityChina;
};

export default isPopulationDensityOfSingaporeHigherThanChina;