// src/main.ts
import { PrismaClient } from '@prisma/client';
import { QueryResponse, QueryResult } from './lib/skills/direct_query/utils/types';
import { countryPopulationDensityQuery } from './lib/skills/direct_query/getCountryPopulationDensity';
import { tokyoWardHospitalStatisticsQuery } from './lib/skills/direct_query/getTokyoWardHospitalStatistics';
import { tokyoWardSchoolStatisticsQuery } from './lib/skills/direct_query/getTokyoWardSchoolStatistics';
import { tokyoWardPopulationDensityQuery } from './lib/skills/direct_query/getTokyoWardPopulationDensity';
import { tokyoWardParkStatisticsQuery } from './lib/skills/direct_query/getTokyoWardParkStatistics';
import { tokyoWardLibraryStatisticsQuery } from './lib/skills/direct_query/getTokyoWardLibraryStatistics';

const prisma = new PrismaClient();

interface QueryConfig<T> {
  name: string;
  type: string;
  execute: () => Promise<QueryResponse<T>>;
  formatResult: (result: QueryResult<T>) => string;
}

const executeQueries = async () => {
  console.log("🗺️  Initializing Geo-Voyager Direct Query System...");

  try {
    const queries: QueryConfig<any>[] = [
      {
        name: '📊 Global Population Density',
        type: 'country_population_density',
        execute: () => countryPopulationDensityQuery.execute(),
        formatResult: (result) => `Most densely populated country: ${result.data.mostDense.country}`
      },
      {
        name: '🏥 Tokyo Ward Hospital Statistics',
        type: 'tokyo_ward_hospitals',
        execute: () => tokyoWardHospitalStatisticsQuery.execute(),
        formatResult: (result) => `Ward with most hospitals: ${result.data.mostHospitals.ward}`
      },
      {
        name: '🏫 Tokyo Ward School Statistics',
        type: 'tokyo_ward_schools',
        execute: () => tokyoWardSchoolStatisticsQuery.execute(),
        formatResult: (result) => `Ward with most schools: ${result.data.mostSchools.ward}`
      },
      {
        name: '👥 Tokyo Ward Population Density',
        type: 'tokyo_ward_density',
        execute: () => tokyoWardPopulationDensityQuery.execute(),
        formatResult: (result) => `Most densely populated ward: ${result.data.mostDense.ward}`
      },
      {
        name: '🌳 Tokyo Ward Park Statistics',
        type: 'tokyo_ward_parks',
        execute: () => tokyoWardParkStatisticsQuery.execute(),
        formatResult: (result) => `Ward with most parks: ${result.data.mostParks.ward}`
      },
      {
        name: '📚 Tokyo Ward Library Statistics',
        type: 'tokyo_ward_libraries',
        execute: () => tokyoWardLibraryStatisticsQuery.execute(),
        formatResult: (result) => `Ward with most libraries: ${result.data.mostLibraries.ward}`
      }
    ];

    for (const query of queries) {
      console.log(`\nExecuting ${query.name}...`);
      try {
        const result = await query.execute();
        if ('data' in result) {
          await prisma.directQueryResult.create({
            data: {
              queryType: query.type,
              result: JSON.parse(JSON.stringify(result.data)),
              metadata: JSON.parse(JSON.stringify(result.metadata))
            }
          });
          console.log(`✅ ${query.formatResult(result)}`);
        } else {
          console.error(`❌ Query failed: ${result.error}`);
        }
      } catch (error) {
        console.error(`❌ Error executing ${query.name}:`, error);
        continue; // Continue with next query even if this one fails
      }
    }

    console.log("\n🗺️  Geo-Voyager has completed all direct queries.");
  } catch (error) {
    console.error("❌ Fatal error executing queries:", error);
  } finally {
    await prisma.$disconnect();
  }
};

executeQueries().catch(console.error);
