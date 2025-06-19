# Open FinOps Stack Modularization Plan

## Vision

Transform the Open FinOps Stack from a monolithic application into a modular, composable platform where users can install only the components they need. This approach maximizes value for different use cases while maintaining the integrated experience for full-stack users.

## Goals

### Developer Experience
- **Monorepo for development** - Single repo for easier CI, testing, and versioning
- **Clean separation** - Core framework separated from vendor-specific implementations
- **Plugin architecture** - Vendors register capabilities via standardized interfaces

### User Experience  
- **Selective installation** - `pip install open-finops[aws]` gets only AWS components
- **Familiar CLI** - Keep existing `./finops aws import-cur` interface
- **Graceful degradation** - Missing vendors fail with helpful error messages

### Ecosystem Growth
- **Vendor modularity** - Each cloud provider can be developed/released independently
- **DBT package compatibility** - Separate `dbt-finops-aws` packages for transformations
- **Third-party extensions** - Clear plugin interfaces for community contributions

## Current State Analysis

### What Works Well
- ✅ Clean CLI interface (`./finops aws import-cur`)
- ✅ Solid core utilities (config, state tracking, table naming)
- ✅ DLT pipeline architecture
- ✅ Comprehensive testing framework

### What Needs Refactoring
- 🔄 AWS code mixed with core framework
- 🔄 Single setup.py for everything
- 🔄 Hard-coded vendor discovery
- 🔄 No plugin registration system

## Target Architecture

### Development Structure (Monorepo)
```
open-finops-stack/
├── core/                           # Core framework package
│   ├── __init__.py
│   ├── config.py                   # Configuration management
│   ├── state.py                    # State tracking infrastructure  
│   ├── utils.py                    # Common utilities
│   ├── cli/                        # Base CLI framework
│   │   ├── __init__.py
│   │   ├── main.py                 # Plugin discovery & routing
│   │   └── base.py                 # Base command classes
│   └── setup.py                    # Core package definition
├── vendors/
│   ├── aws/                        # AWS vendor package
│   │   ├── __init__.py
│   │   ├── pipeline.py             # AWS CUR pipeline
│   │   ├── manifest.py             # AWS-specific manifest handling
│   │   ├── cli.py                  # AWS CLI commands
│   │   └── setup.py                # AWS package definition
│   ├── azure/                      # Future: Azure package
│   └── gcp/                        # Future: GCP package
├── docker/                         # Container configurations
│   ├── core/                       # Base containers
│   ├── aws/                        # AWS-specific containers
│   └── setup.py                    # Docker package definition
├── docs/
│   ├── architecture/               # This documentation
│   └── (existing docs)
├── tests/
│   ├── core/                       # Core framework tests
│   ├── vendors/aws/                # AWS-specific tests
│   └── integration/                # Cross-package integration tests
├── setup.py                        # Main orchestrator with extras
└── pyproject.toml                  # Modern Python packaging
```

### Distribution (PyPI Packages)
```bash
# Core only (framework, no vendors)
pip install open-finops

# Specific vendors
pip install open-finops[aws]         # Core + AWS
pip install open-finops[azure]       # Core + Azure (future)
pip install open-finops[docker]      # Core + Docker configs

# Multiple vendors
pip install open-finops[aws,azure]   # Core + AWS + Azure

# Everything
pip install open-finops[all]         # All available components
```

### Plugin Discovery
```python
# Core CLI discovers vendor commands via entry points
entry_points = {
    'open_finops.vendors': [
        'aws = open_finops_aws.cli:AWSCommands',
        'azure = open_finops_azure.cli:AzureCommands',
    ],
    'open_finops.docker': [
        'compose = open_finops_docker:DockerCompose',
    ]
}
```

## Implementation Phases

### Phase 1: Monorepo Structure (2-3 hours)
**Goal**: Reorganize codebase into modular structure while maintaining functionality

**Deliverables**:
- New directory structure implemented
- Core framework separated from AWS code
- All imports updated and working
- Tests passing

**Details**: [Phase 1: Monorepo Structure](./phase-1-monorepo-structure.md)

### Phase 2: Multi-Package Setup (2-3 hours)  
**Goal**: Create separate setup.py files and plugin registration system

**Deliverables**:
- Individual package definitions (core, aws, docker)
- Plugin discovery system implemented
- Extras-based installation working
- CLI commands discovered dynamically

**Details**: [Phase 2: Multi-Package Setup](./phase-2-multi-package-setup.md)

### Phase 3: Testing & Documentation (1-2 hours)
**Goal**: Ensure all installation scenarios work and document the new structure

**Deliverables**:
- Installation scenarios tested
- Plugin system documented
- Migration guide for existing users
- CI/CD updated for multi-package structure

**Details**: [Phase 3: Testing & Documentation](./phase-3-testing-documentation.md)

## Success Criteria

### Technical Requirements
- [ ] `pip install open-finops` installs core framework only
- [ ] `pip install open-finops[aws]` adds AWS functionality  
- [ ] `./finops aws import-cur` works exactly as before
- [ ] `./finops aws import-cur` fails gracefully if AWS not installed
- [ ] All existing tests pass
- [ ] New vendor packages can be added without touching core

### User Experience Requirements
- [ ] No breaking changes to CLI interface
- [ ] Installation is simpler for users who only need specific vendors
- [ ] Error messages are helpful when vendors are missing
- [ ] Documentation clearly explains installation options

### Development Requirements
- [ ] Single-repo development workflow maintained
- [ ] CI/CD builds and tests all packages
- [ ] Clear interfaces for adding new vendors
- [ ] Plugin registration is straightforward

## Timeline

**Total Estimated Time**: 5-8 hours of focused work

- **Week 1**: Phase 1 (Monorepo Structure)
- **Week 2**: Phase 2 (Multi-Package Setup)  
- **Week 3**: Phase 3 (Testing & Documentation)

## Risk Mitigation

### Potential Issues
1. **Import complexity** - Circular dependencies between packages
2. **Testing overhead** - Need to test all installation combinations
3. **Version compatibility** - Core and vendor versions getting out of sync

### Mitigation Strategies
1. **Clear dependency hierarchy** - Vendors depend on core, never reverse
2. **Automated testing matrix** - CI tests all installation scenarios
3. **Semantic versioning** - Clear compatibility contracts between packages

## Future Considerations

### DBT Package Ecosystem
After modularization, create separate DBT packages:
- `dbt-finops-aws` - AWS CUR → FOCUS transformations
- `dbt-finops-azure` - Azure → FOCUS transformations
- `dbt-finops-gcp` - GCP → FOCUS transformations

### Community Extensions
Plugin architecture enables:
- Third-party vendor integrations
- Custom transformation plugins  
- Alternative output formats
- Specialized analytics tools

## Related Documentation

- [Phase 1: Monorepo Structure](./phase-1-monorepo-structure.md)
- [Phase 2: Multi-Package Setup](./phase-2-multi-package-setup.md)
- [Phase 3: Testing & Documentation](./phase-3-testing-documentation.md)
- [CLI Plugin Discovery Design](./cli-plugin-discovery.md)

---

**Status**: Planning  
**Target Phase**: Phase 2 (Container Runtime) - architecture improvement  
**Dependencies**: None (can run in parallel with Podman work)