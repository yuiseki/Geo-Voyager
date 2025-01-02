// description: シンガポールの人口密度がモナコよりも高いことを確認する。
import * as turf from "@turf/turf";
import osmtogeojson from "osmtogeojson";

/**
 * @return boolean
 */
const isPopulationDensityOfSingaporeHigherThanMonaco = async () => {
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
  const fetchWorldBank = async (countryCode: string): Promise<any> => {
    const endpoint = `https://api.worldbank.org/v2/country/${countryCode}/indicator/SP.POP.TOTL?&format=json`;
    const res = await fetch(endpoint);
    return await res.json();
  };

  // シンガポールの面積と人口を取得
  const querySingapore = `[out:json];
relation["name"="Singapore"]["admin_level"=2];
out geom;`;
  const resultSingapore = await fetchOverpassData(querySingapore);
  const geoJsonSingapore = osmtogeojson(resultSingapore);
  const areaSingapore = turf.area(geoJsonSingapore);
  let populationSingapore = geoJsonSingapore.features[0].properties?.population;
  if (isNaN(populationSingapore)) {
    const result = await fetchWorldBank("sg");
    populationSingapore = result[1][0].value;
  }

  // シンガポールの人口密度を計算
  const populationDensitySingapore = populationSingapore / areaSingapore;

  // モナコの面積と人口を取得
  const queryMonaco = `[out:json];
relation["name"="Monaco"]["admin_level"=2];
out geom;`;
  const resultMonaco = await fetchOverpassData(queryMonaco);
  const geoJsonMonaco = osmtogeojson(resultMonaco);
  const areaMonaco = turf.area(geoJsonMonaco);
  const populationMonaco = geoJsonMonaco.features[0].properties?.population;
  // モナコの人口密度を計算
  const populationDensityMonaco = populationMonaco / areaMonaco;

  return populationDensitySingapore > populationDensityMonaco;
};

export default isPopulationDensityOfSingaporeHigherThanMonaco;
