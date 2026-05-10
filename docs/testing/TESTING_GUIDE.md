# Testing Guide for Developers

## Quick Start

Choose the right script for your situation:

### 🚀 During Active Development
```bash
# Windows
.\scripts\test-fast.ps1

# Linux/macOS
./scripts/test-fast.sh
```
**What it does:** Quick feedback loop - skips slow tests and type checking.
**When to use:** Every few minutes while coding.

---

### 🔍 Before Committing
```bash
# Windows
.\scripts\test-ci.ps1

# Linux/macOS
./scripts/test-ci.sh
```
**What it does:** Full CI test suite - exactly what GitHub Actions runs.
**When to use:** Before `git push` to ensure CI will pass.

---

### 🐛 Fixing Multiple Issues
```bash
# Windows
.\scripts\test-all.ps1

# Linux/macOS
./scripts/test-all.sh
```
**What it does:** Runs ALL tests without stopping - shows complete picture.
**When to use:** When you want to see all failures at once and fix them together.

---

### 📊 Checking Coverage
```bash
# Windows
.\scripts\test-coverage.ps1

# Linux/macOS
./scripts/test-coverage.sh
```
**What it does:** Generates code coverage reports.
**When to use:** Before submitting PR to ensure adequate test coverage.

---

## Detailed Comparison

| Script | Speed | Coverage | Stops on Error | Use Case |
|--------|-------|----------|----------------|----------|
| `test-fast` | ⚡ Fastest | ❌ No | ✅ Yes | Active development |
| `test-ci` | 🐢 Full | ❌ No | ✅ Yes | Pre-commit check |
| `test-all` | 🐢 Full | ❌ No | ❌ No | See all issues |
| `test-coverage` | 🐢 Full | ✅ Yes | ✅ Yes | Coverage analysis |

## What Each Script Runs

### test-fast (⚡ ~3-5 minutes)
- ✅ Linting (ruff)
- ✅ RuleEngine test
- ✅ Security scans
- ✅ OpenAPI diff
- ✅ Alembic migrations
- ✅ Unit tests (parallel, no slow tests)
- ✅ Integration tests (parallel)
- ❌ Type checking (skipped)
- ❌ Slow tests (skipped)

### test-ci (🐢 ~8-12 minutes)
- ✅ Linting (ruff)
- ✅ RuleEngine test
- ✅ Security scans
- ✅ OpenAPI diff
- ✅ Alembic migrations
- ✅ Unit tests (parallel, all tests)
- ✅ Integration tests (parallel)
- ✅ Type checking (mypy)

### test-all (🐢 ~8-12 minutes)
Same as `test-ci`, but:
- ❌ Does NOT stop on first failure
- ✅ Shows summary of ALL failures at the end

### test-coverage (🐢 ~10-15 minutes)
Same as `test-ci`, but:
- ✅ Generates `coverage.xml` report
- ✅ Shows coverage percentage in terminal

## Typical Workflow

### 1. Development Cycle
```bash
# Make changes to code
vim apps/api/services/property_service.py

# Quick test
.\scripts\test-fast.ps1

# Continue coding...
```

### 2. Before Committing
```bash
# Run full CI suite
.\scripts\test-ci.ps1

# If it passes, commit
git add .
git commit -m "feat: add property filtering"
git push
```

### 3. Fixing Multiple Issues
```bash
# See all problems at once
.\scripts\test-all.ps1

# Output shows:
# Failed steps (3):
#   ✗ Ruff linting
#   ✗ Unit tests
#   ✗ Integration tests

# Fix all issues
# ...

# Verify fixes
.\scripts\test-ci.ps1
```

### 4. Coverage Check
```bash
# Before submitting PR
.\scripts\test-coverage.ps1

# Check coverage report
cat apps/api/coverage.xml
```

## Understanding Test Output

### Success ✅
```
=== All CI tests passed! ===
Total time: 08:45
```

### Failure (Normal Mode) ❌
```
ERROR: Unit tests failed!
```
Stops immediately - fix this issue first.

### Failure (test-all Mode) ⚠️
```
=== Test run completed with failures ===

Failed steps (3):
  ✗ Ruff linting
  ✗ Unit tests
  ✗ Integration tests

Note: ContinueOnError mode was enabled - all tests were executed
Fix the issues above and re-run without -ContinueOnError flag

Total time: 08:45
```
Shows ALL failures - fix them all, then re-run.

## Advanced Usage

### Run Specific Test Module
```bash
cd apps/api
python -m pytest tests/unit/api -n auto
```

### Run Single Test
```bash
cd apps/api
python -m pytest tests/unit/api/test_routes.py::test_health_check
```

### Run Tests Matching Pattern
```bash
cd apps/api
python -m pytest -k "property" -n auto
```

### Run Only Slow Tests
```bash
cd apps/api
python -m pytest -m slow
```

### Run Without Parallel Execution
```bash
cd apps/api
python -m pytest tests/unit
```

### Show Test Durations
```bash
cd apps/api
python -m pytest tests/unit --durations=20 -n auto
```

## Troubleshooting

### Tests Pass Locally But Fail in CI

**Cause:** Different Python version or environment.

**Solution:**
```bash
# Check Python version
python --version  # Should be 3.12.x

# Use Python 3.12 environment
cd apps/api
.venv312\Scripts\Activate.ps1  # Windows
source .venv312/bin/activate   # Linux/macOS
```

### Tests Are Slow

**Cause:** Running all tests including slow ones.

**Solution:**
```bash
# Use fast mode
.\scripts\test-fast.ps1
```

### Tests Fail in Parallel

**Cause:** Tests are not atomic/independent.

**Solution:**
```bash
# Run sequentially to debug
cd apps/api
python -m pytest tests/unit/problematic_test.py -v
```

### Coverage Too Low

**Cause:** Missing tests for new code.

**Solution:**
```bash
# Check which files need coverage
.\scripts\test-coverage.ps1

# Look at coverage report
cat apps/api/coverage.xml
```

## Performance Tips

1. **Use `test-fast` during development** - saves time
2. **Run `test-ci` before pushing** - catches issues early
3. **Use `test-all` when fixing multiple issues** - see everything at once
4. **Run specific test modules** - faster than full suite
5. **Mark slow tests** - skip them during development

## CI/CD Integration

### GitHub Actions

The project uses two CI workflows:

**1. Standard CI (`.github/workflows/ci.yml`)**
- Uses pytest-xdist for parallel execution
- Runs on every push/PR
- ~8-12 minutes

**2. Parallel Matrix CI (`.github/workflows/ci-parallel.yml`)**
- Splits tests into 9 parallel jobs
- Runs on every push/PR
- ~5-8 minutes (faster)

Both workflows run the same tests, just with different parallelization strategies.

## Best Practices

### ✅ DO
- Run `test-fast` frequently during development
- Run `test-ci` before every commit
- Use `test-all` when preparing fixes for multiple issues
- Write atomic, independent tests
- Use fixtures for setup/teardown
- Mock external dependencies

### ❌ DON'T
- Skip tests before committing
- Commit code with failing tests
- Write tests that depend on execution order
- Use global state in tests
- Make real API calls in unit tests
- Ignore test failures

## Getting Help

### Documentation
- [Test Optimization Guide](./TEST_OPTIMIZATION.md) - Technical details
- [Parallel Testing Summary](./PARALLEL_TESTING_SUMMARY.md) - Implementation details
- [Scripts README](../../scripts/README.md) - Script documentation

### Common Issues
- Tests fail in parallel → Check for shared state
- Tests are slow → Use `test-fast` or mark slow tests
- Coverage too low → Add more tests
- CI fails but local passes → Check Python version

### Support
- Create an issue on GitHub
- Ask in team chat
- Check existing documentation

## Summary

**Remember these 4 scripts:**

1. **`test-fast`** - Quick feedback during development
2. **`test-ci`** - Full check before committing
3. **`test-all`** - See all issues at once
4. **`test-coverage`** - Check code coverage

That's it! No need to remember complex parameters. 🚀
