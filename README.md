# Company Document Generator and Graph Database

This project provides tools to generate realistic company documents (contracts, invoices, payroll) and load them into a Neo4j graph database for analysis and querying.

## Features

### Document Generation
- Customer Contracts
- Vendor Contracts
- Customer Invoices
- Vendor Invoices
- Employee Payroll Documents
- Department Payroll Reports

### Graph Database Integration
- Schema Management
- Document Ingestion
- Relationship Mapping

## Prerequisites

- [Devbox](https://www.jetpack.io/devbox)
- [Poetry](https://python-poetry.org/)
- [Neo4j](https://neo4j.com/) (local or cloud instance)
- OpenAI API access
- Llama Parse API access

## Getting Started

1. **Set up Development Environment**
   ```bash
   devbox shell
   poetry install
   ```

2. **Configure Environment Variables**

   Copy the example environment file and configure your settings:
   ```bash
   cp .env.example .env
   ```

   Required environment variables:
   - `NEO4J_URI`: Your Neo4j database URI (default: neo4j://localhost:7687)
   - `NEO4J_USERNAME`: Neo4j database username
   - `NEO4J_PASSWORD`: Neo4j database password
   - `OPENAI_API_KEY`: Your OpenAI API key for contract generation
   - `LLAMA_PARSE_API_KEY`: Your Llama Parse API key for document parsing

3. **Generate Company Documents**

   Run the following generators to create sample documents:
   ```bash
   # Generate customer contracts
   poetry run python -m src.generators.generate_contracts

   # Generate vendor contracts
   poetry run python -m src.generators.generate_vendor_contracts

   # Generate customer invoices
   poetry run python -m src.generators.generate_invoices

   # Generate vendor invoices
   poetry run python -m src.generators.generate_vendor_invoices

   # Generate payroll documents
   poetry run python -m src.generators.generate_payrolls
   ```

4. **Set up Graph Database**

   Apply the graph schema:
   ```bash
   poetry run python -m src.graph.apply_schema
   ```

5. **Load Documents into Graph Database**

   Ingest generated documents:
   ```bash
   poetry run python -m src.graph.loader
   ```

## Generated Documents

All generated documents are stored in the `company_documents` directory with the following structure:
