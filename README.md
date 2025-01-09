# Geo-Voyager: An Open-Ended Autonomous AI Agent Mining Uncharted Real-World Geospatial Insights

[English](./README.md) | [日本語](./README.ja.md)

Geo-Voyager is an autonomous AI agent system that maximizes geospatial insights about the real world by iteratively generating questions, formulating hypotheses, and verifying them using generative AI.

## Overview

Geo-Voyager uses LangChain and Ollama to drive an autonomous cycle of:
- Generating interesting questions about real-world geospatial patterns
- Formulating testable hypotheses
- Collecting and analyzing data from OpenStreetMap and other sources
- Building a library of verified insights and reusable analysis skills

## Features

- **Question Generation**: Generates interesting questions about real-world geospatial patterns
- **Hypothesis Creation & Verification**: Formulates hypotheses and verifies them through data collection and analysis
- **Data Collection**: Gathers necessary data from OpenStreetMap Overpass API and other sources
- **Skills Library**: Accumulates successful API queries and analysis code as reusable skills
- **Hypothesis & Insight Library**: Records generated hypotheses and verification results as accumulated insights

## Prerequisites

- Node.js (v18 or later)
- npm
- SQLite
- Ollama with qwen2.5:14b model

### Installing Ollama

1. Install Ollama:
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

2. Start Ollama:
```bash
ollama serve
```

3. Pull the qwen2.5:14b model:
```bash
ollama pull qwen2.5:14b
```

## Installation

1. Clone the repository:
```bash
gh repo clone yuiseki/Geo-Voyager
cd Geo-Voyager
```

2. Install dependencies:
```bash
npm install
```

3. Set up the database:
```bash
# Create .env file with SQLite database URL
echo "DATABASE_URL=\"file:./prisma/dev.db\"" > .env

# Initialize the database
make clean
```

## Usage

The project uses make commands for common operations:

### Make Commands

- `make all` - Initialize database and start the system (recommended)
- `make main` - Start the system (checks for database and runs migrations if needed)
- `make migrate` - Initialize/reset the database and run migrations
- `make clean` - Clean the database and reinitialize it

To start the system with a fresh database:
```bash
make all
```

To start the system with existing database:
```bash
make main
```

## System Flow

Geo-Voyager discovers geospatial insights through these iterative steps:

1. **Question Generation**: Uses generative AI to create questions about real-world geospatial patterns
2. **Hypothesis Formulation**: Creates testable hypotheses for generated questions
3. **Hypothesis Verification**: Collects and analyzes data to verify hypothesis validity
4. **Insight Recording**: Records successful hypotheses as verified insights
5. **Skill Improvement**: Accumulates and improves data collection and analysis processes as reusable skills

For detailed system flow, see the [flowchart](./docs/flowchart-overview.md).

## Documentation

- [Requirements and Architecture](./docs/requirements.md)
- [Skills Development Guide](./src/lib/skills/README.md)
- [Issues Analysis](./docs/analysis/issues-analysis.md)

## Development

### Project Structure

- `src/` - Main source code
  - `lib/skills/` - Reusable analysis skills
- `prisma/` - Database schema and migrations
- `docs/` - Project documentation

### Database Schema

The project uses Prisma with SQLite for:
- Questions and their states
- Hypotheses and verification results
- Tasks for hypothesis verification
- Reusable skills library

See [schema.prisma](./prisma/schema.prisma) for details.

### Contributing

1. Create a new branch for your changes
2. Follow the coding conventions in [Skills README](./src/lib/skills/README.md)
3. Ensure all skills are independent and self-contained
4. Add appropriate documentation for new features
5. Submit a pull request with a clear description of changes

## License

WTFPL

## Technical Details

- Built with TypeScript and Node.js
- Uses LangChain with Ollama (qwen2.5:14b model) for AI operations
- Prisma ORM with SQLite for data management
- OpenStreetMap Overpass API for geospatial data
- Additional data sources: World Bank, UN OCHA HDX
