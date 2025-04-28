// description: 東京都において、病院の数が最も多い行政区を探す。
// file_path: src/lib/skills/numberOfSchools/Japan/Tokyo/findWardWithMostHospitals.ts

import { fetchOverpassData } from "../../../common/fetchOverpassData";
import { getAllWardsInTokyo } from "./ward/getAllWardsInTokyo";

/**
 * Fetches the number of hospitals in a specified ward using Overpass API.
 * @param wardName - The name of the ward to query.
 * @returns The total count of hospitals in the ward.
 */
async function getHospitalCountByWard(wardName: string): Promise<number> {
  const overpassQuery = `
[out:json];
area["name"="東京都"]->.out;
area["name"="${wardName}"]->.in;
(
  nwr["amenity"="hospital"](area.in)(area.out);
);
out count;
`;

  const response = await fetchOverpassData(overpassQuery);
  return response.elements[0].tags.total;
}

export const findWardWithMostHospitals = async (): Promise<string> => {
  const wards = await getAllWardsInTokyo();
  let maxHospitals = 0;
  let wardWithMostHospitals = "";
  for (const ward of wards) {
    const hospitalCount = await getHospitalCountByWard(ward);
    if (hospitalCount > maxHospitals) {
      maxHospitals = hospitalCount;
      wardWithMostHospitals = ward;
    }
  }
  return wardWithMostHospitals;
};
