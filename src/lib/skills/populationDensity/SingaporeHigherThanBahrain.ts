// description: シンガポールの人口密度がバーレーンよりも高いことを確認する。
import * as turf from "@turf/turf";
import osmtogeojson from "osmtogeojson";

/**
 * @returns boolean
 */
const isPopulationDensityOfSingaporeHigherThanBahrain = async () => {
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

  // バーレーンの面積と人口を取得
  const queryBahrain = `[out:json];
relation["name:en"="Bahrain"]["admin_level"=2];
out geom;`;
  const resultBahrain = await fetchOverpassData(queryBahrain);
  const geoJsonBahrain = osmtogeojson(resultBahrain);
  const areaBahrain = turf.area(geoJsonBahrain);
  let populationBahrain = geoJsonBahrain.features[0].properties?.population;
  if (isNaN(populationBahrain)) {
    const result = await fetchWorldBank("bh");
    populationBahrain = result[1][0].value;
  }

  // バーレーンの人口密度を計算
  const populationDensityBahrain = populationBahrain / areaBahrain;

  return populationDensitySingapore > populationDensityBahrain;
};

export default isPopulationDensityOfSingaporeHigherThanBahrain;
