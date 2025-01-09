-- CreateTable
CREATE TABLE "DirectQueryResult" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "queryType" TEXT NOT NULL,
    "result" JSONB NOT NULL,
    "timestamp" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "metadata" JSONB
);
