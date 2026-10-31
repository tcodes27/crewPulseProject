# CrewPulse | Flight Operations Analytics

CrewPulse is a data engineering and analytics portfolio project that demonstrates how flight operations data can be collected, organized, validated, analyzed, and presented through an interactive Tableau dashboard.

The project uses **synthetic data** to explore flight performance, crew coverage, airport information, and operational trends.

## Project Goals

- Build a structured PostgreSQL database for flight operations.
- Develop data validation and quality checks.
- Use SQL to analyze flight performance and crew coverage.
- Create reusable analytics views.
- Export analytical datasets for visualization.
- Present operational insights through Tableau Public.

## Technology Stack

- **Python** — data processing and pipeline workflows
- **PostgreSQL 17** — relational database
- **SQL** — data analysis, transformations, and views
- **Git and GitHub** — version control
- **Tableau Public** — data visualization
- **pytest** — automated testing

## Data Architecture

The database is organized into four schemas:

| Schema | Purpose |
|---|---|
| `raw` | Source data |
| `core` | Structured operational data |
| `ops` | Pipeline runs and data quality results |
| `analytics` | Views prepared for analysis and reporting |

### Core Tables

- `core.airports`
- `core.crew_members`
- `core.flights`
- `core.crew_assignments`
- `core.crew_assignment_history`

### Operations Tables

- `ops.pipeline_runs`
- `ops.data_quality_results`

## Data Quality and Validation

The project includes checks for:

- Duplicate airport identifiers
- Required fields and valid airport codes
- Referential integrity
- Flight and crew assignment relationships
- Assignment history and date consistency
- Duplicate assignments
- Crew coverage requirements

Automated tests: **13 passed**.

## Analytics

The analytics layer includes three PostgreSQL views:

- `analytics.vw_flight_performance_by_origin`
- `analytics.vw_crew_coverage_by_flight`
- `analytics.vw_route_activity`

Additional SQL analysis examines flight delays by scheduled departure hour.

### Key Findings

| Metric | Result |
|---|---:|
| Airports | 9,053 |
| Flights | 200 |
| Crew members | 100 |
| Crew assignments | 400 |
| Delayed flights | 45 |
| Overall delay rate | 22.50% |
| Flights with adequate crew coverage | 200 |
| Crew coverage rate | 100% |

Departure-hour analysis identified differences in delay rates across hours with at least eight flights. The highest observed rates were 37.50% at 11:00 and 19:00.

These findings describe the synthetic project dataset only. They should not be interpreted as actual airline operating patterns or evidence of causation.

## Tableau Dashboard

**CrewPulse | Flight Operations Analytics**

[View the interactive Tableau dashboard](https://public.tableau.com/views/CrewPulseFlightOperationsAnalytics/Dashboard1)

The dashboard presents:
- Flight volume and delay rates by departure hour
- Crew coverage performance
- Route-level flight activity

## Exported Datasets

The repository includes CSV exports used to build the Tableau visualizations:

- `flight_performance_by_origin.csv`
- `crew_coverage_by_flight.csv`
- `route_activity.csv`
- `delay_analysis_by_departure_hour.csv`

## Testing

Run the automated test suite from the project root:

```bash
python -m pytest -q

## Project Purpose 

CrewPulse demonstrates practical skills in data engineering, relational database design, SQL analysis, data quality validation, version control, and business intelligence. 


## Data Disclaimer

CrewPulse is an independent portfolio demonstration project using synthetic flight, crew, airport, and operational data. It does not represent actual Delta Air Lines operations, employees, schedules, or performance. All metrics and visualizations are provided for demonstration and analytical learning purposes only.  
