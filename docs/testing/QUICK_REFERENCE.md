# Testing Quick Reference

## 🚀 One-Line Commands

### Windows

```powershell
.\scripts\test-fast.ps1       # ⚡ Quick test (3-5 min)
.\scripts\test-ci.ps1         # 🔍 Full CI (8-12 min)
.\scripts\test-all.ps1        # 🐛 See all failures (8-12 min)
.\scripts\test-coverage.ps1   # 📊 Coverage report (10-15 min)
```

### Linux/macOS

```bash
./scripts/test-fast.sh        # ⚡ Quick test (3-5 min)
./scripts/test-ci.sh          # 🔍 Full CI (8-12 min)
./scripts/test-all.sh         # 🐛 See all failures (8-12 min)
./scripts/test-coverage.sh    # 📊 Coverage report (10-15 min)
```

## 📖 When to Use What

| Situation | Script | Why |
|-----------|--------|-----|
| Coding right now | `test-fast` | Quick feedback, skip slow tests |
| About to commit | `test-ci` | Ensure CI will pass |
| Multiple failures | `test-all` | See everything at once |
| Before PR | `test-coverage` | Check coverage |

## 💡 Examples

### During Development

```bash
# Make changes
vim apps/api/services/property_service.py

# Quick test
.\scripts\test-fast.ps1

# Continue coding...
```

### Before Commit

```bash
# Full check
.\scripts\test-ci.ps1

# If passes, commit
git add .
git commit -m "feat: add feature"
git push
```

### Fixing Multiple Issues

```bash
# See all problems
.\scripts\test-all.ps1

# Output:
# Failed steps (3):
#   ✗ Ruff linting
#   ✗ Unit tests
#   ✗ Integration tests

# Fix all, then verify
.\scripts\test-ci.ps1
```

## 🔧 Advanced Usage

Need more control? Use the advanced script:

```powershell
# Windows
.\scripts\run_ci_tests_local.ps1 -Fast -Coverage

# Linux/macOS
./scripts/run_ci_tests_local.sh --fast --coverage
```

## 📚 Full Documentation

- [Testing Guide](./TESTING_GUIDE.md) - Complete guide
- [Test Optimization](./TEST_OPTIMIZATION.md) - Technical details
- [Scripts README](../../scripts/README.md) - All scripts

## ❓ Help

**Tests fail?** Check [Troubleshooting](./TESTING_GUIDE.md#troubleshooting)

**Need coverage?** Use `test-coverage`

**Want to see all issues?** Use `test-all`

**Just coding?** Use `test-fast`

---

**That's it! Just remember 4 scripts:** `test-fast`, `test-ci`, `test-all`, `test-coverage` 🎯
