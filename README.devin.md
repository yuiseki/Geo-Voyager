# Geo-Voyager - Devin's Operation Verification Guide

This guide is specifically written for Devin to verify the operation of Geo-Voyager, an autonomous AI agent for geospatial insights generation and verification.

## Prerequisites Verification

First, verify all required components are installed:

```bash
# Verify Node.js (v18+ required)
node --version  # Should output v18.x.x or higher

# Verify npm
npm --version   # Should output version number

# Verify SQLite3
sqlite3 --version  # Should output version number

# Verify Ollama
which ollama  # Should output path to ollama
```

If any components are missing, install them:

```bash
# Install SQLite3
sudo apt-get update && sudo apt-get install -y sqlite3

# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh
```

## Environment Setup

1. Clone the repository:
```bash
gh repo clone yuiseki/Geo-Voyager
cd Geo-Voyager
```

2. Start Ollama service and pull required model:
```bash
# Start Ollama service (if not already running)
ollama serve &

# Pull the required model
ollama pull qwen2.5:14b
```

3. Install project dependencies:
```bash
npm install
```

4. Set up database configuration:
```bash
echo "DATABASE_URL=\"file:./prisma/dev.db\"" > .env
```

5. Initialize the database:
```bash
make clean
```

## Operation Verification

1. Start the system:
```bash
make all
```

Expected behavior:
- Database initialization should complete without errors
- System should start and begin generating questions
- You should see output related to hypothesis generation and verification

## Common Issues and Solutions

1. SQLite3 not found:
   - Solution: Install using `sudo apt-get install -y sqlite3`

2. Ollama model download issues:
   - Solution: Ensure Ollama service is running with `ollama serve`
   - Verify network connectivity
   - Retry model pull with `ollama pull qwen2.5:14b`

3. Database initialization fails:
   - Solution: Ensure SQLite3 is installed
   - Check .env file exists with correct DATABASE_URL
   - Try `make clean` to reset the database

## Success Criteria

The system is working correctly when:
1. All prerequisites are installed and verified
2. Database initialization completes successfully
3. The system starts without errors using `make all`
4. Questions and hypotheses are being generated
5. The system can interact with OpenStreetMap Overpass API

## Project Structure Overview

Key components to verify:
- `/src/`: Main source code
- `/prisma/`: Database schema and migrations
- `/docs/`: Additional documentation
- `package.json`: Project dependencies
- `Makefile`: System commands

## Notes for Devin

1. Always verify prerequisites before attempting to run the system
2. The system requires active internet connection for OpenStreetMap API access
3. GPU is not required but can enhance performance if available
4. The system is designed to run continuously, generating and verifying geospatial hypotheses
5. Use `make clean` to reset the system if you encounter issues

## Verification Workflow

1. Check prerequisites ✓
2. Install missing components ✓
3. Set up environment ✓
4. Initialize database ✓
5. Start system ✓
6. Verify output and operation ✓

Remember to monitor the system's output for any errors and verify that it's actively generating and testing geospatial hypotheses.
