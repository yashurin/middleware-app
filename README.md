# middleware-app

A data middleware application built with FastAPI, React, MariaDB, and Apicurio schema registry, orchestrated through Docker Compose.

## Technologies

- **Backend**: FastAPI (Python)
- **Frontend**: React
- **Database**: MariaDB
- **Schema Registry**: Apicurio
- **Deployment**: Docker Compose

## Overview

middleware-app is a specialized middleware solution that acts as an intermediary for data processing workflows. The application:

1. Exposes API endpoints to consume incoming data
2. Validates data against predefined schemas stored in Apicurio registry
3. Transforms and updates the data structure as needed
4. Persists both incoming and outgoing data in MariaDB
5. Forwards processed data to schema-specific destination URLs

This architecture enables reliable data validation, transformation, and routing while maintaining a complete audit trail of all transactions.

## Prerequisites

- Docker & Docker Compose
- Git

## Setup & Installation

1. Clone the repository
   ```bash
   git clone git@github.com:yashurin/middleware-app.git
   cd middleware-app
   ```

2. Configure environment variables
   ```bash
   to be added
   ```

3. Start the application
   ```bash
   docker compose build
   docker compose up -d
   ```

4. Access the application
   - Frontend: http://localhost:3000
   - API: http://localhost:8000/
   - API Documentation: http://localhost:8000/docs
   - Apicurio Registry UI: http://localhost:8081/ui/artifacts

## Usage

### Managing Schemas

TO DO: To be added

### Processing Data

Send data to the API endpoint with the appropriate schema identifier:

```bash
TO DO: to be added
```

The middleware will:
- Validate the data against the specified schema
- Transform the data according to configured rules
- Store both original and transformed data
- Forward the processed data to the schema-specific destination

## API Documentation

API documentation is available at http://localhost:8000/docs when the application is running.

## Development

### Local Development Setup

TO DO: to be added

## License

This project is licensed under the MIT License - see the LICENSE file for details.

# middleware-app
A middleware Demo application


### Query records from the DB

http://localhost:8000/records?schema_name=contact-message-schema

### Query records from the DB with limit and offset

http://localhost:8000/records?schema_name=contact-message-schema&limit=10&offset=10


