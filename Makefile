
all: migrate main

.SILENT: main
main:
	@test -f prisma/dev.db || $(MAKE) migrate
	npx tsx --network-family-autoselection-attempt-timeout=500 ./src/main.ts

migrate:
	test -f prisma/dev.db && rm prisma/dev.db || true
	npx prisma migrate dev --name init
	npx prisma generate

clean:
	test -f prisma/dev.db && rm prisma/dev.db || true
	npx prisma migrate dev --name init
	npx prisma generate
