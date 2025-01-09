/*
  Warnings:

  - You are about to drop the column `metadata` on the `DirectQueryResult` table. All the data in the column will be lost.

*/
-- RedefineTables
PRAGMA defer_foreign_keys=ON;
PRAGMA foreign_keys=OFF;
CREATE TABLE "new_DirectQueryResult" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "queryType" TEXT NOT NULL,
    "result" JSONB NOT NULL,
    "timestamp" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
INSERT INTO "new_DirectQueryResult" ("id", "queryType", "result", "timestamp") SELECT "id", "queryType", "result", "timestamp" FROM "DirectQueryResult";
DROP TABLE "DirectQueryResult";
ALTER TABLE "new_DirectQueryResult" RENAME TO "DirectQueryResult";
PRAGMA foreign_keys=ON;
PRAGMA defer_foreign_keys=OFF;
