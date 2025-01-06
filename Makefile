
all: main

.SILENT: main
main:
	npx tsx --network-family-autoselection-attempt-timeout=500 ./src/main.ts

migrate:
	rm prisma/dev.db
	npx prisma migrate dev --name init
	npx prisma generate

clean:
	rm prisma/dev.db
	npx prisma migrate dev --name init
	npx prisma generate
