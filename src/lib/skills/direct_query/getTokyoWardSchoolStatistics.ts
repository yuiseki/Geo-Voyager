import { BaseDirectQuery } from './utils/BaseDirectQuery';
import { QueryResponse } from './utils/types';
import { fetchWithCache } from './utils/fetchWithCache';

interface SchoolData {
  ward: string;
  totalSchools: number;
  schoolsPerPopulation: number;
  population: number;
  schoolTypes: {
    elementary: number;
    junior_high: number;
    high_school: number;
    university: number;
  };
}

interface SchoolQueryResult {
  mostSchools: SchoolData;
  mostSchoolsPerCapita: SchoolData;
  allWards: SchoolData[];
  rankings: {
    byTotal: { [key: string]: number };
    byPerCapita: { [key: string]: number };
    byType: {
      elementary: { [key: string]: number };
      junior_high: { [key: string]: number };
      high_school: { [key: string]: number };
      university: { [key: string]: number };
    };
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
    const populationData = await fetchWithCache(
      'https://api.data.metro.tokyo.lg.jp/v1/WardPopulation',
      {
        directory: 'tokyo',
        ttlSeconds: this.CACHE_TTL
      }
    );

    const populations = new Map<string, number>();
    for (const ward of populationData) {
      populations.set(ward.ward_name, ward.population);
    }
    return populations;
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
      const rankings = {
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
      ['elementary', 'junior_high', 'high_school', 'university'].forEach(type => {
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
