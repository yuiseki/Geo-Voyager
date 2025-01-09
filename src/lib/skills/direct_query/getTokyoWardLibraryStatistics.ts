import { BaseDirectQuery } from './utils/BaseDirectQuery';
import { QueryResponse, Rankings, TypeRankings, LibraryTypes, LibraryTypeKey } from './utils/types';
import { fetchWithCache } from './utils/fetchWithCache';

interface LibraryData {
  ward: string;
  totalLibraries: number;
  librariesPerPopulation: number;
  population: number;
  libraryTypes: LibraryTypes;
}

interface LibraryQueryResult {
  mostLibraries: LibraryData;
  mostLibrariesPerCapita: LibraryData;
  allWards: LibraryData[];
  rankings: {
    byTotal: Rankings;
    byPerCapita: Rankings;
    byType: TypeRankings;
  };
}

export class TokyoWardLibraryStatisticsQuery extends BaseDirectQuery<LibraryQueryResult> {
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

  private async fetchLibrariesInWard(wardName: string): Promise<LibraryData['libraryTypes']> {
    const query = `
      [out:json][timeout:25];
      area["name:en"="${wardName}"]["admin_level"="8"]->.ward;
      (
        // Public libraries
        node["amenity"="library"]["library"="public"](area.ward);
        way["amenity"="library"]["library"="public"](area.ward);
        relation["amenity"="library"]["library"="public"](area.ward);
        // University libraries
        node["amenity"="library"]["library"="university"](area.ward);
        way["amenity"="library"]["library"="university"](area.ward);
        relation["amenity"="library"]["library"="university"](area.ward);
        // School libraries
        node["amenity"="library"]["library"="school"](area.ward);
        way["amenity"="library"]["library"="school"](area.ward);
        relation["amenity"="library"]["library"="school"](area.ward);
        // Special libraries (research, private, etc.)
        node["amenity"="library"]["library"!~"public|university|school"](area.ward);
        way["amenity"="library"]["library"!~"public|university|school"](area.ward);
        relation["amenity"="library"]["library"!~"public|university|school"](area.ward);
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
      public_library: data.elements[0]?.tags?.library === 'public' ? data.elements[0].count : 0,
      university_library: data.elements[0]?.tags?.library === 'university' ? data.elements[0].count : 0,
      school_library: data.elements[0]?.tags?.library === 'school' ? data.elements[0].count : 0,
      special_library: data.elements[0]?.tags?.library === 'special' ? data.elements[0].count : 0
    };
  }

  async execute(): Promise<QueryResponse<LibraryQueryResult>> {
    try {
      const tokyoWards = [
        'Adachi', 'Arakawa', 'Bunkyo', 'Chiyoda', 'Chuo',
        'Edogawa', 'Itabashi', 'Katsushika', 'Kita', 'Koto',
        'Meguro', 'Minato', 'Nakano', 'Nerima', 'Ota',
        'Setagaya', 'Shibuya', 'Shinagawa', 'Shinjuku', 'Suginami',
        'Sumida', 'Taito', 'Toshima'
      ];

      const wardData: LibraryData[] = [];
      const populations = await this.fetchWardPopulations();

      // Fetch library data for all wards
      for (const ward of tokyoWards) {
        await this.rateLimiter.waitForNext();
        const libraryTypes = await this.fetchLibrariesInWard(ward);
        const population = populations.get(ward) || 0;
        const totalLibraries = Object.values(libraryTypes).reduce((a, b) => a + b, 0);
        
        wardData.push({
          ward,
          totalLibraries,
          libraryTypes,
          population,
          librariesPerPopulation: population > 0 ? (totalLibraries / population) * 100000 : 0
        });
      }

      // Sort by various metrics
      const byTotal = [...wardData].sort((a, b) => b.totalLibraries - a.totalLibraries);
      const byPerCapita = [...wardData].sort((a, b) => b.librariesPerPopulation - a.librariesPerPopulation);

      // Calculate rankings
      const rankings: {
        byTotal: Rankings;
        byPerCapita: Rankings;
        byType: { [K in LibraryTypeKey]: Rankings };
      } = {
        byTotal: {},
        byPerCapita: {},
        byType: {
          public_library: {},
          university_library: {},
          school_library: {},
          special_library: {}
        }
      };

      byTotal.forEach((ward, index) => {
        rankings.byTotal[ward.ward] = index + 1;
      });

      byPerCapita.forEach((ward, index) => {
        rankings.byPerCapita[ward.ward] = index + 1;
      });

      // Rankings by library type
      (['public_library', 'university_library', 'school_library', 'special_library'] as LibraryTypeKey[]).forEach(type => {
        const sorted = [...wardData].sort((a, b) => 
          b.libraryTypes[type] - a.libraryTypes[type]
        );
        sorted.forEach((ward, index) => {
          rankings.byType[type][ward.ward] = index + 1;
        });
      });

      const result: LibraryQueryResult = {
        mostLibraries: byTotal[0],
        mostLibrariesPerCapita: byPerCapita[0],
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
export const tokyoWardLibraryStatisticsQuery = new TokyoWardLibraryStatisticsQuery();
