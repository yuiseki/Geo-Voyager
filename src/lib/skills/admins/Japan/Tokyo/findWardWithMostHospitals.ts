// description: 東京都において、病院の数が最も多い行政区を探す。
// file_path: src/lib/skills/numberOfSchools/Japan/Tokyo/findWardWithMostHospitals.ts

import { getAllWardsInTokyo } from "./ward/getAllWardsInTokyo";
import { getHospitalsCountByWard } from "./ward/getHospitalsCountByWard";

export const findWardWithMostHospitals = async (): Promise<string> => {
  const wards = await getAllWardsInTokyo();
  let maxHospitals = 0;
  let wardWithMostHospitals = "";
  for (const ward of wards) {
    const hospitalCount = await getHospitalsCountByWard(ward);
    if (hospitalCount > maxHospitals) {
      maxHospitals = hospitalCount;
      wardWithMostHospitals = ward;
    }
  }
  return wardWithMostHospitals;
};
