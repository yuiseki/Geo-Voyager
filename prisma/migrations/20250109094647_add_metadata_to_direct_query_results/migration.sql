/*
  Warnings:

  - Added the required column `metadata` to the `DirectQueryResult` table without a default value. This is not possible if the table is not empty.

*/
-- RedefineTables
PRAGMA defer_foreign_keys=ON;
PRAGMA foreign_keys=OFF;
CREATE TABLE "new_DirectQueryResult" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "queryType" TEXT NOT NULL,
    "result" JSONB NOT NULL,
    "timestamp" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "metadata" JSONB NOT NULL
);
INSERT INTO "new_DirectQueryResult" ("id", "queryType", "result", "timestamp") SELECT "id", "queryType", "result", "timestamp" FROM "DirectQueryResult";
DROP TABLE "DirectQueryResult";
ALTER TABLE "new_DirectQueryResult" RENAME TO "DirectQueryResult";
PRAGMA foreign_keys=ON;
PRAGMA defer_foreign_keys=OFF;
