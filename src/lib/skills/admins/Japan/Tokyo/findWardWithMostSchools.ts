// description: 東京都において、学校の数が最も多い行政区を探す。
// file_path: src/lib/skills/admins/Japan/Tokyo/findWardWithMostSchools.ts

import { getAllWardsInTokyo } from "./ward/getAllWardsInTokyo";
import { getSchoolsCountByWard } from "./ward/getSchoolsCountByWard";

const findWardWithMostSchools = async (): Promise<string> => {
  const wards = await getAllWardsInTokyo();
  let maxSchools = 0;
  let wardWithMostSchools = "";
  for (const ward of wards) {
    const schoolCount = await getSchoolsCountByWard(ward);
    if (schoolCount > maxSchools) {
      maxSchools = schoolCount;
      wardWithMostSchools = ward;
    }
  }
  return wardWithMostSchools;
};

export default findWardWithMostSchools;
