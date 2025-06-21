# DuckLake Backend Implementation Plan

## Overview

This document details the implementation plan for adding DuckLake backend support to the Open FinOps Stack. DuckLake is a new lakehouse format that uses SQL databases for metadata management while storing data in open formats like Parquet, providing transactional capabilities and advanced features like time travel.

## Architecture Integration

### Current Architecture
```
S3 CUR Data → DuckDB Database → Analytics/Visualization
```

### Proposed DuckLake Architecture
```
S3 CUR Data → DuckLake Storage → DuckDB Views → Analytics/Visualization
```

## Implementation Strategy

### Phase 1: Core Backend Implementation

#### 1.1 Configuration Extension
**File**: `src/core/backends/base.py`

Add DuckLakeConfig class:
```python
@dataclass
class DuckLakeConfig(BackendConfig):
    """Configuration for DuckLake backend."""
    backend_type: str = "ducklake"
    database_path: str = "./data/finops.ducklake"
    duckdb_path: str = "./data/finops-ducklake.duckdb"  # DuckDB instance for metadata
    compression: str = "zstd"
    enable_encryption: bool = False
    partition_strategy: str = "monthly"  # monthly, yearly, account
```

#### 1.2 Backend Implementation
**File**: `src/core/backends/ducklake.py`

Core components:
- `DuckLakeBackend`: Main backend implementation
- `DuckLakeStateManager`: Transactional state management
- `DuckLakeDataReader`: S3 data reading with DuckLake integration

#### 1.3 DLT Integration Strategy
**Approach**: Leverage DuckDB destination with DuckLake attachment

```python
def get_dlt_destination(self):
    """Create DLT destination that writes to DuckLake."""
    import dlt
    
    # Create DuckDB destination with DuckLake attached
    destination = dlt.destinations.duckdb(
        credentials=f"{self.config.duckdb_path}"
    )
    
    # Post-connection setup will attach DuckLake
    return destination
```

### Phase 2: Advanced Features

#### 2.1 Transactional Import Operations
- Multi-account atomic imports
- Rollback capability on import failures
- Concurrent import support

#### 2.2 Time Travel Capabilities
- Historical cost analysis
- Point-in-time billing snapshots
- Audit trail for data changes

#### 2.3 Schema Evolution
- Automatic handling of AWS CUR format changes  
- Backward compatibility for queries
- Column mapping strategies

## Detailed Implementation Plan

### Step 1: DuckLake Extension Setup

**Prerequisites**:
- DuckDB v1.3.0+ (DuckLake extension availability)
- Python duckdb package with extension support

**Installation Process**:
```python
import duckdb

def setup_ducklake_connection(db_path: str, ducklake_path: str):
    """Setup DuckDB connection with DuckLake extension."""
    conn = duckdb.connect(db_path)
    conn.execute("INSTALL ducklake")
    conn.execute("LOAD ducklake")
    conn.execute(f"ATTACH 'ducklake:{ducklake_path}' AS finops_lake")
    return conn
```

### Step 2: State Management Implementation

**DuckLakeStateManager Features**:
- Transactional state tracking using DuckLake tables
- Version history with timestamps
- Multi-account load coordination
- Failure recovery mechanisms

**State Schema**:
```sql
-- DuckLake state management tables
CREATE TABLE finops_lake.load_states (
    version_id VARCHAR PRIMARY KEY,
    account_id VARCHAR,
    export_name VARCHAR,
    load_start_time TIMESTAMP,
    load_end_time TIMESTAMP,
    status VARCHAR, -- 'started', 'completed', 'failed'
    record_count BIGINT,
    file_paths VARCHAR[]
);

CREATE TABLE finops_lake.schema_versions (
    version_id VARCHAR PRIMARY KEY,
    schema_hash VARCHAR,
    column_mappings JSON,
    created_at TIMESTAMP
);
```

### Step 3: Data Reader Implementation

**DuckLakeDataReader Strategy**:
1. **Direct S3 Integration**: Use DuckLake's S3 capabilities if available
2. **Hybrid Approach**: Download to temp, process with DuckLake
3. **Streaming Support**: Handle large CUR files efficiently

**Implementation**:
```python
class DuckLakeDataReader(DataReader):
    def read_parquet_file(self, s3_uri: str) -> Iterator[Dict[str, Any]]:
        """Read parquet file directly into DuckLake table."""
        # Strategy 1: Direct S3 read if supported
        if self.supports_direct_s3():
            return self._read_s3_direct(s3_uri)
        
        # Strategy 2: Download and process
        return self._read_via_download(s3_uri)
```

### Step 4: Table Organization Strategy

**Atomic Monthly Partition Replacement**:

DuckLake's transactional capabilities enable **atomic table replacement** similar to ClickHouse, but with better consistency guarantees:

```sql
-- Strategy: Transactional table replacement for monthly partitions
BEGIN TRANSACTION;

-- 1. Create new table with updated data
CREATE TABLE finops_lake.aws_billing_${account_id}_${year}_${month}_new AS
SELECT * FROM read_parquet('s3://bucket/new-cur-data/*.parquet');

-- 2. Atomically replace the old table
DROP TABLE IF EXISTS finops_lake.aws_billing_${account_id}_${year}_${month};
ALTER TABLE finops_lake.aws_billing_${account_id}_${year}_${month}_new 
RENAME TO aws_billing_${account_id}_${year}_${month};

COMMIT;
```

**Key Advantages over ClickHouse**:
1. **True ACID Transactions**: Either the entire month replacement succeeds or fails
2. **Multi-Table Consistency**: Replace multiple account tables atomically
3. **Zero-Downtime**: Readers see consistent data throughout the replacement
4. **Rollback Support**: Failed replacements don't leave partial data

**Partitioning Schema**:
```sql
-- Monthly partitioned tables per AWS account
CREATE TABLE finops_lake.aws_billing_${account_id}_${year}_${month} (
    -- AWS CUR columns with proper types
    lineitem_lineitemid VARCHAR,
    lineitem_usagestartdate TIMESTAMP,
    lineitem_usageenddate TIMESTAMP,
    lineitem_productcode VARCHAR,
    lineitem_usagetype VARCHAR,
    lineitem_operation VARCHAR,
    lineitem_availabilityzone VARCHAR,
    lineitem_resourceid VARCHAR,
    lineitem_usageamount DOUBLE,
    lineitem_normalizationfactor DOUBLE,
    lineitem_normalizedusageamount DOUBLE,
    lineitem_currencycode VARCHAR,
    lineitem_unblendedrate DOUBLE,
    lineitem_unblendedcost DOUBLE,
    lineitem_blendedrate DOUBLE,
    lineitem_blendedcost DOUBLE,
    -- ... additional AWS CUR columns
    _dlt_load_id VARCHAR,
    _dlt_id VARCHAR
);
```

**Replacement Pipeline**:
```python
class DuckLakeStateManager(StateManager):
    def replace_monthly_partition(self, account_id: str, year: int, month: int, s3_data_path: str):
        """Atomically replace monthly partition with new CUR data."""
        table_name = f"aws_billing_{account_id}_{year}_{month:02d}"
        temp_table = f"{table_name}_new"
        
        with self.conn.begin():
            # Create new table with updated data
            self.conn.execute(f"""
                CREATE TABLE finops_lake.{temp_table} AS
                SELECT * FROM read_parquet('{s3_data_path}')
            """)
            
            # Atomically replace
            self.conn.execute(f"DROP TABLE IF EXISTS finops_lake.{table_name}")
            self.conn.execute(f"ALTER TABLE finops_lake.{temp_table} RENAME TO {table_name}")
            
            # Update load state
            self.complete_load(version_id, record_count=self.conn.execute(f"SELECT COUNT(*) FROM finops_lake.{table_name}").fetchone()[0])
```

### Step 5: Configuration Integration

**config.toml Extensions**:
```toml
[database]
backend = "ducklake"

[database.ducklake]
database_path = "./data/finops.ducklake"
duckdb_path = "./data/finops-ducklake.duckdb"
compression = "zstd"
enable_encryption = false
partition_strategy = "monthly"

# Performance tuning
[database.ducklake.performance]
max_concurrent_loads = 4
chunk_size = 50000
memory_limit = "2GB"
```

### Step 6: Testing Strategy

**Test Categories**:

1. **Unit Tests**:
   - DuckLake connection setup/teardown
   - State management operations
   - Configuration validation
   - Data reader functionality

2. **Integration Tests**:
   - End-to-end CUR import pipeline
   - Multi-account import scenarios
   - Schema evolution testing
   - Time travel functionality

3. **Performance Tests**:
   - Large dataset import benchmarks
   - Concurrent load testing
   - Query performance comparisons

**Test Data Strategy**:
```python
# Test fixtures for DuckLake backend
@pytest.fixture
def ducklake_backend():
    """Create temporary DuckLake backend for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = DuckLakeConfig(
            database_path=f"{tmpdir}/test.ducklake",
            duckdb_path=f"{tmpdir}/test.duckdb"
        )
        yield DuckLakeBackend(config)
```

## Migration Strategy

### Existing Data Migration

**Migration Path**: DuckDB → DuckLake
```sql
-- Export existing DuckDB data
COPY (SELECT * FROM aws_billing.billing_2024_01) 
TO 'migration_data.parquet' (FORMAT PARQUET);

-- Import into DuckLake
CREATE TABLE finops_lake.aws_billing_account1_2024_01 AS 
SELECT * FROM read_parquet('migration_data.parquet');
```

### Backward Compatibility

**View Layer**: Create DuckDB views over DuckLake tables
```sql
-- Compatibility views for existing queries
CREATE VIEW aws_billing.billing_2024_01 AS 
SELECT * FROM finops_lake.aws_billing_account1_2024_01;
```

## Performance Considerations

### Expected Benefits

1. **Transactional Safety**: Atomic multi-account imports
2. **Storage Efficiency**: Lakehouse format with compression
3. **Query Performance**: Optimized for analytical workloads
4. **Concurrent Access**: Multiple readers/writers support
5. **Time Travel**: Historical analysis without data duplication

### Potential Challenges

1. **DLT Integration**: May need custom destination implementation
2. **Extension Stability**: DuckLake is experimental in DuckDB v1.3.0
3. **Learning Curve**: New API and concepts for developers
4. **Debugging**: Additional complexity for troubleshooting

## Rollout Plan

### Phase 1: Core Implementation (1-2 weeks)
- [ ] DuckLake backend implementation
- [ ] Basic configuration support
- [ ] Unit test coverage
- [ ] CLI integration

### Phase 2: Advanced Features (1-2 weeks)
- [ ] Transactional operations
- [ ] Time travel functionality
- [ ] Schema evolution support
- [ ] Performance optimization

### Phase 3: Production Readiness (1 week)
- [ ] Integration test suite
- [ ] Migration tooling
- [ ] Documentation updates
- [ ] Deployment guides

## Risks and Mitigations

### Risk 1: DuckLake Extension Instability
**Mitigation**: 
- Comprehensive testing with realistic data
- Fallback to DuckDB backend option
- Version pinning for DuckDB/DuckLake

### Risk 2: DLT Integration Complexity  
**Mitigation**:
- Start with simple DuckDB destination approach
- Custom DLT destination if needed
- Maintain existing pipeline compatibility

### Risk 3: Performance Regression
**Mitigation**:
- Benchmark against current DuckDB performance
- Optimize table organization and indexing
- Configurable backend selection

## Success Criteria

1. **Functional Parity**: All existing DuckDB backend features work
2. **Performance**: No significant regression in import/query performance  
3. **Reliability**: Stable operation with multi-account imports
4. **Usability**: Simple configuration switch between backends
5. **Extensibility**: Foundation for advanced lakehouse features

## Next Steps

1. **Review and Approval**: Stakeholder review of this implementation plan
2. **Proof of Concept**: Simple DuckLake connection and table creation
3. **Backend Implementation**: Core DuckLakeBackend class development
4. **Testing Framework**: Unit and integration test development
5. **Documentation**: User guides and deployment instructions

This implementation leverages the existing backend abstraction system to add DuckLake support with minimal disruption to current functionality while enabling advanced lakehouse capabilities for the Open FinOps Stack.