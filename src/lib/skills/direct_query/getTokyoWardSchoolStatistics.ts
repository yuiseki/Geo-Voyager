import { BaseDirectQuery } from './utils/BaseDirectQuery';
import { QueryResponse, Rankings, TypeRankings, SchoolTypes, SchoolTypeKey } from './utils/types';
import { fetchWithCache } from './utils/fetchWithCache';

interface SchoolData {
  ward: string;
  totalSchools: number;
  schoolsPerPopulation: number;
  population: number;
  schoolTypes: SchoolTypes;
}

interface SchoolQueryResult {
  mostSchools: SchoolData;
  mostSchoolsPerCapita: SchoolData;
  allWards: SchoolData[];
  rankings: {
    byTotal: Rankings;
    byPerCapita: Rankings;
    byType: TypeRankings;
  };
}

export class TokyoWardSchoolStatisticsQuery extends BaseDirectQuery<SchoolQueryResult> {
  private readonly CACHE_PATH = './tmp/cache/osm/tokyo_ward_schools.json';
  private readonly CACHE_TTL = 43200; // 12 hours in seconds

  constructor() {
    // Set rate limit to 2 calls per second as per Overpass API guidelines
    super(2);
  }

  private async fetchWardPopulations(): Promise<Map<string, number>> {
    // Mock population data for testing
    const mockPopulationData = [
      { ward_name: 'Adachi', population: 692000 },
      { ward_name: 'Arakawa', population: 217000 },
      { ward_name: 'Bunkyo', population: 233000 },
      { ward_name: 'Chiyoda', population: 66000 },
      { ward_name: 'Chuo', population: 169000 },
      { ward_name: 'Edogawa', population: 698000 },
      { ward_name: 'Itabashi', population: 570000 },
      { ward_name: 'Katsushika', population: 448000 },
      { ward_name: 'Kita', population: 341000 },
      { ward_name: 'Koto', population: 527000 },
      { ward_name: 'Meguro', population: 280000 },
      { ward_name: 'Minato', population: 258000 },
      { ward_name: 'Nakano', population: 328000 },
      { ward_name: 'Nerima', population: 737000 },
      { ward_name: 'Ota', population: 737000 },
      { ward_name: 'Setagaya', population: 932000 },
      { ward_name: 'Shibuya', population: 224000 },
      { ward_name: 'Shinagawa', population: 408000 },
      { ward_name: 'Shinjuku', population: 347000 },
      { ward_name: 'Suginami', population: 582000 },
      { ward_name: 'Sumida', population: 270000 },
      { ward_name: 'Taito', population: 186000 },
      { ward_name: 'Toshima', population: 300000 }
    ];
    return new Map(mockPopulationData.map(ward => [ward.ward_name, ward.population]));
  }

  private async fetchSchoolsInWard(wardName: string): Promise<SchoolData['schoolTypes']> {
    const query = `
      [out:json][timeout:25];
      area["name:en"="${wardName}"]["admin_level"="8"]->.ward;
      (
        // Elementary schools
        node["amenity"="school"]["isced:level"="1"](area.ward);
        way["amenity"="school"]["isced:level"="1"](area.ward);
        relation["amenity"="school"]["isced:level"="1"](area.ward);
        // Junior high schools
        node["amenity"="school"]["isced:level"="2"](area.ward);
        way["amenity"="school"]["isced:level"="2"](area.ward);
        relation["amenity"="school"]["isced:level"="2"](area.ward);
        // High schools
        node["amenity"="school"]["isced:level"="3"](area.ward);
        way["amenity"="school"]["isced:level"="3"](area.ward);
        relation["amenity"="school"]["isced:level"="3"](area.ward);
        // Universities
        node["amenity"="university"](area.ward);
        way["amenity"="university"](area.ward);
        relation["amenity"="university"](area.ward);
      );
      out count;
    `;

    const data = await fetchWithCache(
      `https://overpass-api.de/api/interpreter?data=${encodeURIComponent(query)}`,
      {
        directory: 'osm',
        ttlSeconds: this.CACHE_TTL
      }
    );

    return {
      elementary: data.elements[0]?.tags?.['isced:level'] === '1' ? data.elements[0].count : 0,
      junior_high: data.elements[0]?.tags?.['isced:level'] === '2' ? data.elements[0].count : 0,
      high_school: data.elements[0]?.tags?.['isced:level'] === '3' ? data.elements[0].count : 0,
      university: data.elements[0]?.tags?.amenity === 'university' ? data.elements[0].count : 0
    };
  }

  async execute(): Promise<QueryResponse<SchoolQueryResult>> {
    try {
      const tokyoWards = [
        'Adachi', 'Arakawa', 'Bunkyo', 'Chiyoda', 'Chuo',
        'Edogawa', 'Itabashi', 'Katsushika', 'Kita', 'Koto',
        'Meguro', 'Minato', 'Nakano', 'Nerima', 'Ota',
        'Setagaya', 'Shibuya', 'Shinagawa', 'Shinjuku', 'Suginami',
        'Sumida', 'Taito', 'Toshima'
      ];

      const wardData: SchoolData[] = [];
      const populations = await this.fetchWardPopulations();

      // Fetch school data for all wards
      for (const ward of tokyoWards) {
        await this.rateLimiter.waitForNext();
        const schoolTypes = await this.fetchSchoolsInWard(ward);
        const totalSchools = Object.values(schoolTypes).reduce((a, b) => a + b, 0);
        const population = populations.get(ward) || 0;
        
        wardData.push({
          ward,
          totalSchools,
          schoolTypes,
          population,
          schoolsPerPopulation: population > 0 ? (totalSchools / population) * 100000 : 0
        });
      }

      // Sort by various metrics
      const byTotal = [...wardData].sort((a, b) => b.totalSchools - a.totalSchools);
      const byPerCapita = [...wardData].sort((a, b) => b.schoolsPerPopulation - a.schoolsPerPopulation);
      
      // Calculate rankings
      const rankings: {
        byTotal: Rankings;
        byPerCapita: Rankings;
        byType: { [K in SchoolTypeKey]: Rankings };
      } = {
        byTotal: {},
        byPerCapita: {},
        byType: {
          elementary: {},
          junior_high: {},
          high_school: {},
          university: {}
        }
      };

      byTotal.forEach((ward, index) => {
        rankings.byTotal[ward.ward] = index + 1;
      });

      byPerCapita.forEach((ward, index) => {
        rankings.byPerCapita[ward.ward] = index + 1;
      });

      // Rankings by school type
      (['elementary', 'junior_high', 'high_school', 'university'] as SchoolTypeKey[]).forEach(type => {
        const sorted = [...wardData].sort((a, b) => 
          b.schoolTypes[type] - a.schoolTypes[type]
        );
        sorted.forEach((ward, index) => {
          rankings.byType[type][ward.ward] = index + 1;
        });
      });

      const result: SchoolQueryResult = {
        mostSchools: byTotal[0],
        mostSchoolsPerCapita: byPerCapita[0],
        allWards: wardData,
        rankings
      };

      return {
        data: result,
        metadata: {
          timestamp: Date.now(),
          source: 'OpenStreetMap Overpass API',
          cacheHit: false
        }
      };
    } catch (error) {
      return this.handleError(error);
    }
  }
}

// Export singleton instance
export const tokyoWardSchoolStatisticsQuery = new TokyoWardSchoolStatisticsQuery();
