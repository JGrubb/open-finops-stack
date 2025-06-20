# Database Backend Implementation Plan

## Project Vision

Transform the Open FinOps Stack from a DuckDB-only solution to a **database-agnostic platform** that can integrate with any enterprise data warehouse or analytical database. Organizations should be able to use their existing data infrastructure (Snowflake, BigQuery, PostgreSQL, etc.) while leveraging the same powerful AWS billing pipeline.

## Current State Analysis

### Well-Abstracted Components ✅
- **DLT Pipeline**: Already uses `dlt.destinations.*` for backend switching
- **Data Loading**: DLT handles schema creation, type mapping, and write dispositions  
- **Configuration**: TOML-based config easily supports new backend sections

### Tightly Coupled Components ❌
- **State Management**: `core/state.py` uses direct DuckDB connections (8 locations)
- **S3 Reading**: `vendors/aws/pipeline.py` uses DuckDB's `httpfs` extension  
- **SQL Operations**: Pipeline uses DuckDB-specific queries and functions
- **Database Path**: Hardcoded `./data/finops.duckdb` assumptions

## Implementation Plan

### Phase 1: Foundation & Interfaces (2-3 hours)

**Goal**: Create the abstract backend system and migrate existing DuckDB functionality into the new architecture.

#### Step 1.1: Create Backend Interface Hierarchy
- **File**: `core/backends/__init__.py`
- **File**: `core/backends/base.py`
  - `BackendConfig` dataclass hierarchy
  - `DatabaseBackend` abstract interface
  - `StateManager` abstract interface  
  - `DataReader` abstract interface

#### Step 1.2: Create Backend Factory System
- **File**: `core/backends/factory.py`
  - `create_backend()` factory function
  - Environment variable integration
  - Configuration validation

#### Step 1.3: Extend Configuration Schema
- **File**: `core/config.py`
  - Add `DatabaseConfig` class
  - Support for multiple backend types
  - Backward compatibility with existing configs
- **File**: `config.toml.example`
  - Add `[database]` section examples
  - Document all supported backends

#### Step 1.4: Update Project Dependencies
- **File**: `requirements.txt` or `pyproject.toml`
  - Add optional dependencies for backends
  - Example: `snowflake-connector-python[pandas]`
  - Use extras pattern: `pip install open-finops[snowflake]`

### Phase 2: DuckDB Backend Migration (1-2 hours)

**Goal**: Extract existing DuckDB functionality into the new backend system without changing behavior.

#### Step 2.1: Create DuckDB Backend Implementation
- **File**: `core/backends/duckdb.py`
  - `DuckDBBackend` class
  - `DuckDBConfig` dataclass
  - `DuckDBStateManager` (migrate from `core/state.py`)
  - `DuckDBDataReader` (migrate S3 reading from pipeline)

#### Step 2.2: Update State Management
- **File**: `core/state.py` → **Refactor**
  - Replace direct DuckDB usage with backend interface
  - Create `LoadStateTracker` that uses `StateManager` interface
  - Maintain existing API for backward compatibility

#### Step 2.3: Update AWS Pipeline
- **File**: `vendors/aws/pipeline.py` → **Refactor**
  - Replace direct DuckDB connections with backend interface
  - Use `DataReader` interface for S3 reading
  - Update `run_aws_pipeline()` to accept backend parameter

### Phase 3: Multi-Backend Support (2-3 hours)

**Goal**: Implement support for enterprise databases (Snowflake, BigQuery, PostgreSQL).

#### Step 3.1: Snowflake Backend
- **File**: `core/backends/snowflake.py`
  - `SnowflakeBackend` class
  - `SnowflakeConfig` with warehouse/database/schema
  - `SnowflakeStateManager` using Snowflake tables
  - `SnowflakeDataReader` with External Stages

#### Step 3.2: BigQuery Backend  
- **File**: `core/backends/bigquery.py`
  - `BigQueryBackend` class
  - `BigQueryConfig` with project/dataset configuration
  - `BigQueryStateManager` using BigQuery tables
  - `BigQueryDataReader` with External Tables

#### Step 3.3: PostgreSQL Backend
- **File**: `core/backends/postgresql.py`
  - `PostgreSQLBackend` class  
  - `PostgreSQLConfig` with connection parameters
  - `PostgreSQLStateManager` using PostgreSQL tables
  - `PostgreSQLDataReader` (boto3 fallback)

#### Step 3.4: Generic SQL Backend (Fallback)
- **File**: `core/backends/sql.py`
  - `GenericSQLBackend` for any SQL database
  - `Boto3DataReader` as universal fallback
  - Support for any DLT-supported destination

### Phase 4: CLI & Configuration Integration (1 hour)

**Goal**: Update CLI and configuration to support backend selection.

#### Step 4.1: Update CLI Interface
- **File**: `core/cli/main.py`
  - Add `--backend` flag to override config
  - Support `--database-config` for additional parameters
  - Environment variable support (`OPEN_FINOPS_DATABASE_BACKEND`)

#### Step 4.2: Update AWS CLI Commands
- **File**: `vendors/aws/cli.py`
  - Pass backend configuration to pipeline
  - Update help text with backend examples
  - Add backend validation

#### Step 4.3: Configuration Examples
- **File**: `examples/config-snowflake.toml`
- **File**: `examples/config-bigquery.toml`  
- **File**: `examples/config-postgresql.toml`

### Phase 5: Testing & Documentation (1-2 hours)

**Goal**: Ensure all backends work correctly and are well documented.

#### Step 5.1: Backend Testing
- **File**: `tests/unit/test_backends.py`
  - Test backend factory creation
  - Test configuration validation
  - Mock tests for each backend type

#### Step 5.2: Integration Testing
- **File**: `tests/integration/test_multi_backend.py`
  - Test DuckDB backend (existing functionality)
  - Test configuration switching
  - Test state management across backends

#### Step 5.3: Documentation Updates
- **File**: `docs/BACKENDS.md`
  - Complete backend setup guide
  - Configuration examples for each backend
  - Performance considerations
- **File**: `README.md`
  - Update with multi-backend support
  - Add backend-specific installation examples

#### Step 5.4: Update Installation Documentation
- **File**: `docs/INSTALLATION.md`
  - Add backend-specific installation steps
  - Document optional dependencies
  - Add troubleshooting section

## Detailed File Changes

### New Files to Create

```
core/backends/
├── __init__.py
├── base.py           # Abstract interfaces
├── factory.py        # Backend creation
├── duckdb.py         # DuckDB implementation  
├── snowflake.py      # Snowflake implementation
├── bigquery.py       # BigQuery implementation
├── postgresql.py     # PostgreSQL implementation
└── sql.py           # Generic SQL fallback

examples/
├── config-snowflake.toml
├── config-bigquery.toml
└── config-postgresql.toml

docs/
└── BACKENDS.md

tests/
├── unit/test_backends.py
└── integration/test_multi_backend.py
```

### Files to Modify

```
core/config.py                    # Add DatabaseConfig
core/state.py                     # Abstract state management
vendors/aws/pipeline.py           # Use backend interfaces
vendors/aws/cli.py                # Add backend parameters
core/cli/main.py                  # Add --backend flag
requirements.txt                  # Add optional dependencies
config.toml.example               # Add database sections
docs/INSTALLATION.md              # Backend setup
README.md                         # Multi-backend usage
```

## Configuration Schema Design

### Base Configuration
```toml
[project]
name = "open-finops-stack"

[database]
backend = "duckdb"  # Default, backward compatible

[aws]
# Existing AWS config unchanged
```

### Backend-Specific Configurations
```toml
# DuckDB (default)
[database.duckdb]
database_path = "./data/finops.duckdb"

# Snowflake
[database.snowflake]
account = "your-account.snowflakecomputing.com"
warehouse = "FINOPS_WH"
database = "FINOPS_DB"
schema = "AWS_BILLING"
user = "finops_user"
role = "FINOPS_ROLE"
# password via SNOWFLAKE_PASSWORD env var

# BigQuery
[database.bigquery]
project_id = "your-gcp-project"
dataset = "finops_data"
location = "US"
# credentials via GOOGLE_APPLICATION_CREDENTIALS

# PostgreSQL
[database.postgresql]
host = "localhost"
port = 5432
database = "finops"
schema = "aws_billing"
user = "finops_user"
# password via POSTGRESQL_PASSWORD env var
```

## Usage Examples

### CLI Usage
```bash
# Default DuckDB (backward compatible)
./finops aws import-cur

# Use Snowflake
./finops aws import-cur --backend snowflake

# Use specific config file
./finops aws import-cur --config snowflake-config.toml

# Override via environment
OPEN_FINOPS_DATABASE_BACKEND=bigquery ./finops aws import-cur
```

### Programmatic Usage
```python
from core.backends.factory import create_backend
from core.config import Config

config = Config.from_file("config.toml")
backend = create_backend(config.database)
pipeline = backend.get_dlt_destination()
```

## Backward Compatibility Strategy

### Existing Users
- All existing `config.toml` files continue to work
- Default backend remains DuckDB
- Existing `./data/finops.duckdb` files are preserved
- No breaking changes to CLI interface

### Migration Path
1. **Phase 1-2**: No user-visible changes (internal refactoring)
2. **Phase 3**: New backends available as opt-in features
3. **Phase 4**: CLI gains `--backend` flag as optional feature
4. **Phase 5**: Full documentation for migration

## Testing Strategy

### Unit Tests
- Backend factory creation
- Configuration validation  
- State manager interfaces
- Data reader interfaces

### Integration Tests
- DuckDB backend (existing functionality)
- Backend switching without data loss
- Configuration file parsing
- CLI flag handling

### Manual Testing Checklist
- [ ] Existing DuckDB workflows unchanged
- [ ] Snowflake connection and data loading
- [ ] BigQuery connection and data loading
- [ ] PostgreSQL connection and data loading
- [ ] Configuration file validation
- [ ] CLI backend switching
- [ ] State management across backends
- [ ] Error handling and validation

## Performance Considerations

### S3 Reading Performance
1. **Native S3 Capabilities** (Fastest)
   - DuckDB: `httpfs` extension
   - Snowflake: External Stages
   - BigQuery: External Tables

2. **Fallback Strategy** (Slower but universal)
   - boto3 + pandas/pyarrow
   - Download to temp files for large datasets
   - Memory-efficient streaming for smaller files

### Database Performance
- **DuckDB**: Excellent for local development and small-medium datasets
- **Snowflake**: Best for large-scale enterprise workloads
- **BigQuery**: Optimal for GCP-native deployments
- **PostgreSQL**: Good balance for self-hosted enterprise

## Risk Mitigation

### Development Risks
- **Breaking Changes**: Extensive testing with existing configurations
- **Performance Regression**: Benchmark DuckDB before/after refactoring
- **Complexity**: Keep interfaces simple and well-documented

### User Adoption Risks
- **Learning Curve**: Maintain simple defaults and clear documentation
- **Migration Effort**: Provide automated migration tools where possible
- **Configuration Complexity**: Use sensible defaults and environment variables

## Success Metrics

### Technical Metrics
- [ ] All existing tests pass
- [ ] DuckDB performance unchanged
- [ ] Successful data loading to 3+ backends
- [ ] Configuration validation covers all backends

### User Experience Metrics
- [ ] Existing users can upgrade without changes
- [ ] New backend setup takes <10 minutes
- [ ] Clear error messages for configuration issues
- [ ] Documentation covers all common use cases

## Next Steps

1. **Review & Edit**: Review this plan and make any necessary adjustments
2. **Create Branch**: `git checkout -b feature/database-backend-abstraction`
3. **Phase 1**: Start with backend interfaces and factory system
4. **Incremental Implementation**: Complete each phase with testing
5. **User Validation**: Test with real Snowflake/BigQuery instances

This plan transforms Open FinOps into a true multi-backend platform while maintaining the simplicity and power that makes it valuable for organizations of all sizes.