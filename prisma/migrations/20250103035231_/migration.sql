/*
  Warnings:

  - Added the required column `updatedAt` to the `HypothesisTask` table without a default value. This is not possible if the table is not empty.
  - Added the required column `updatedAt` to the `Skill` table without a default value. This is not possible if the table is not empty.

*/
-- RedefineTables
PRAGMA defer_foreign_keys=ON;
PRAGMA foreign_keys=OFF;
CREATE TABLE "new_HypothesisTask" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "hypothesisId" INTEGER NOT NULL,
    "taskId" INTEGER NOT NULL,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL,
    CONSTRAINT "HypothesisTask_hypothesisId_fkey" FOREIGN KEY ("hypothesisId") REFERENCES "Hypothesis" ("id") ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT "HypothesisTask_taskId_fkey" FOREIGN KEY ("taskId") REFERENCES "Task" ("id") ON DELETE RESTRICT ON UPDATE CASCADE
);
INSERT INTO "new_HypothesisTask" ("createdAt", "hypothesisId", "id", "taskId") SELECT "createdAt", "hypothesisId", "id", "taskId" FROM "HypothesisTask";
DROP TABLE "HypothesisTask";
ALTER TABLE "new_HypothesisTask" RENAME TO "HypothesisTask";
CREATE TABLE "new_Skill" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "description" TEXT NOT NULL,
    "code" TEXT NOT NULL,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL
);
INSERT INTO "new_Skill" ("code", "createdAt", "description", "id") SELECT "code", "createdAt", "description", "id" FROM "Skill";
DROP TABLE "Skill";
ALTER TABLE "new_Skill" RENAME TO "Skill";
PRAGMA foreign_keys=ON;
PRAGMA defer_foreign_keys=OFF;
