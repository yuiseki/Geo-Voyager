/*
  Warnings:

  - You are about to drop the column `name` on the `AnalyzeSkill` table. All the data in the column will be lost.
  - You are about to drop the column `name` on the `FetchSkill` table. All the data in the column will be lost.

*/
-- RedefineTables
PRAGMA defer_foreign_keys=ON;
PRAGMA foreign_keys=OFF;
CREATE TABLE "new_AnalyzeSkill" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "description" TEXT NOT NULL,
    "code" TEXT NOT NULL,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
INSERT INTO "new_AnalyzeSkill" ("code", "createdAt", "description", "id") SELECT "code", "createdAt", "description", "id" FROM "AnalyzeSkill";
DROP TABLE "AnalyzeSkill";
ALTER TABLE "new_AnalyzeSkill" RENAME TO "AnalyzeSkill";
CREATE TABLE "new_FetchSkill" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "description" TEXT NOT NULL,
    "code" TEXT NOT NULL,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
INSERT INTO "new_FetchSkill" ("code", "createdAt", "description", "id") SELECT "code", "createdAt", "description", "id" FROM "FetchSkill";
DROP TABLE "FetchSkill";
ALTER TABLE "new_FetchSkill" RENAME TO "FetchSkill";
PRAGMA foreign_keys=ON;
PRAGMA defer_foreign_keys=OFF;
