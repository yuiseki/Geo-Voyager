// src/main.ts
import { prisma } from "./db";

(async () => {
  const hypotheses = await prisma.hypothesis.findMany();
  hypotheses.forEach((hypothesis) => {
    console.log(hypothesis.description);
  });
})();
