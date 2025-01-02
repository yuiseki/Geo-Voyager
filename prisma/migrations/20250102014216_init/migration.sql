-- AlterTable
ALTER TABLE "Hypothesis" ADD COLUMN "details" TEXT;

-- CreateTable
CREATE TABLE "Task" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "description" TEXT NOT NULL,
    "status" TEXT NOT NULL,
    "result" TEXT,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" DATETIME NOT NULL
);

-- CreateTable
CREATE TABLE "HypothesisTask" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "hypothesisId" INTEGER NOT NULL,
    "taskId" INTEGER NOT NULL,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "HypothesisTask_hypothesisId_fkey" FOREIGN KEY ("hypothesisId") REFERENCES "Hypothesis" ("id") ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT "HypothesisTask_taskId_fkey" FOREIGN KEY ("taskId") REFERENCES "Task" ("id") ON DELETE RESTRICT ON UPDATE CASCADE
);
