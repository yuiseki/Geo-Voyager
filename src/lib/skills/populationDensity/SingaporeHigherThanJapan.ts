// description: シンガポールの人口密度が日本よりも高いことを確認する。
// file_path: src/lib/skills/populationDensity/SingaporeHigherThanJapan.ts
import * as turf from "@turf/turf";
import osmtogeojson from "osmtogeojson";

/**
 * @return boolean
 */
const isPopulationDensityOfSingaporeHigherThanJapan = async () => {
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
  const fetchWorldBank = async (countryCode: string): Promise<any> => {
    const endpoint = `https://api.worldbank.org/v2/country/${countryCode}/indicator/SP.POP.TOTL?&format=json`;
    const res = await fetch(endpoint);
    return await res.json();
  };

  // シンガポールの面積を取得
  const querySingapore = `[out:json];
relation["name"="Singapore"]["admin_level"=2];
out geom;`;
  const resultSingapore = await fetchOverpassData(querySingapore);
  const geoJsonSingapore = osmtogeojson(resultSingapore);
  const areaSingapore = turf.area(geoJsonSingapore);
  // シンガポールの人口を取得
  let populationSingapore = geoJsonSingapore.features[0].properties?.population;
  if (isNaN(populationSingapore)) {
    const result = await fetchWorldBank("sg");
    populationSingapore = result[1][0].value;
  }
  // シンガポールの人口密度を計算
  const populationDensitySingapore = populationSingapore / areaSingapore;

  // 日本の面積を取得
  const queryJapan = `[out:json];
relation["name:en"="Japan"]["admin_level"=2];
out geom;`;
  const resultJapan = await fetchOverpassData(queryJapan);
  const geoJsonJapan = osmtogeojson(resultJapan);
  const areaJapan = turf.area(geoJsonJapan);
  // 日本の人口を取得
  let populationJapan = geoJsonJapan.features[0].properties?.population;
  if (isNaN(populationJapan)) {
    const result = await fetchWorldBank("jp");
    populationJapan = result[1][0].value;
  }
  // 日本の人口密度を計算
  const populationDensityJapan = populationJapan / areaJapan;

  return populationDensitySingapore > populationDensityJapan;
};

export default isPopulationDensityOfSingaporeHigherThanJapan;
