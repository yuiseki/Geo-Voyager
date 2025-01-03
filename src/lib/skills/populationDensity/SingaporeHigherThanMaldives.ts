// description: シンガポールの人口密度がモルディブよりも高いことを確認する。
// file_path: src/lib/skills/populationDensity/SingaporeHigherThanMaldives.ts
import * as turf from "@turf/turf";
import osmtogeojson from "osmtogeojson";

/**
 * @return boolean
 */
const isPopulationDensityOfSingaporeHigherThanMaldives = async () => {
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

  // モルディブの面積を取得
  const queryMaldives = `[out:json];
relation["name:en"="Maldives"]["admin_level"=2];
out geom;`;
  const resultMaldives = await fetchOverpassData(queryMaldives);
  const geoJsonMaldives = osmtogeojson(resultMaldives);
  const areaMaldives = turf.area(geoJsonMaldives);
  // モルディブの人口を取得
  let populationMaldives = geoJsonMaldives.features[0].properties?.population;
  if (isNaN(populationMaldives)) {
    const result = await fetchWorldBank("mv");
    populationMaldives = result[1][0].value;
  }
  // モルディブの人口密度を計算
  const populationDensityMaldives = populationMaldives / areaMaldives;

  return populationDensitySingapore > populationDensityMaldives;
};

export default isPopulationDensityOfSingaporeHigherThanMaldives;
