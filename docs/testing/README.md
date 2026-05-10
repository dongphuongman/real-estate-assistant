# Testing Documentation

## 📚 Documentation Index

### For Developers (Start Here!)

1. **[Quick Reference](./QUICK_REFERENCE.md)** ⭐
   - One-page cheat sheet
   - 4 simple commands to remember
   - Perfect for daily use

2. **[Testing Guide](./TESTING_GUIDE.md)**
   - Complete user guide
   - Detailed examples
   - Troubleshooting tips

### For Technical Details

3. **[Test Optimization](./TEST_OPTIMIZATION.md)**
   - Parallel execution details
   - Performance tuning
   - Technical implementation

4. **[Parallel Testing Summary](./PARALLEL_TESTING_SUMMARY.md)**
   - Implementation overview
   - Architecture decisions
   - Performance metrics

### For Project Management

5. **[Post-Test Checklist](./POST_TEST_CHECKLIST.md)**
   - What to do after tests complete
   - Documentation updates
   - Commit checklist

6. **[Changelog](./CHANGELOG.md)**
   - Recent changes
   - Version history
   - Migration guide

## 🚀 Quick Start

### I just want to run tests!

**Windows:**
```powershell
.\scripts\test-fast.ps1       # Quick test
.\scripts\test-ci.ps1         # Full CI
```

**Linux/macOS:**
```bash
./scripts/test-fast.sh        # Quick test
./scripts/test-ci.sh          # Full CI
```

**See [Quick Reference](./QUICK_REFERENCE.md) for more.**

## 📖 Which Document Should I Read?

| Your Goal | Read This |
|-----------|-----------|
| I want to run tests quickly | [Quick Reference](./QUICK_REFERENCE.md) |
| I need detailed testing guide | [Testing Guide](./TESTING_GUIDE.md) |
| I want to understand parallel execution | [Test Optimization](./TEST_OPTIMIZATION.md) |
| I need to update documentation | [Post-Test Checklist](./POST_TEST_CHECKLIST.md) |
| I want to see what changed | [Changelog](./CHANGELOG.md) |

## 🎯 Common Tasks

### During Development
→ [Quick Reference](./QUICK_REFERENCE.md#during-development)

### Before Committing
→ [Testing Guide](./TESTING_GUIDE.md#before-committing)

### Fixing Multiple Issues
→ [Testing Guide](./TESTING_GUIDE.md#fixing-multiple-issues)

### Checking Coverage
→ [Testing Guide](./TESTING_GUIDE.md#checking-coverage)

## 🔧 Advanced Topics

### Parallel Execution
→ [Test Optimization](./TEST_OPTIMIZATION.md#parallel-execution)

### Test Atomicity
→ [Parallel Testing Summary](./PARALLEL_TESTING_SUMMARY.md#test-atomicity)

### CI/CD Integration
→ [Testing Guide](./TESTING_GUIDE.md#cicd-integration)

### Performance Tuning
→ [Test Optimization](./TEST_OPTIMIZATION.md#performance-tuning)

## 📊 Test Statistics

- **Total Tests:** 6,254+ (unit) + integration
- **Coverage:** 90%+ (unit), 70%+ (integration)
- **Execution Time:**
  - Fast mode: ~3-5 minutes
  - Full CI: ~8-12 minutes
  - With coverage: ~10-15 minutes
- **Parallel Workers:** Auto-detected (typically 8-16)

## 🛠️ Available Scripts

| Script | Purpose | Time |
|--------|---------|------|
| `test-fast` | Quick feedback | 3-5 min |
| `test-ci` | Full CI suite | 8-12 min |
| `test-all` | See all failures | 8-12 min |
| `test-coverage` | Coverage reports | 10-15 min |

**See [Scripts README](../../scripts/README.md) for details.**

## 🐛 Troubleshooting

Common issues and solutions:
→ [Testing Guide - Troubleshooting](./TESTING_GUIDE.md#troubleshooting)

## 📞 Getting Help

1. Check [Quick Reference](./QUICK_REFERENCE.md) first
2. Read [Testing Guide](./TESTING_GUIDE.md) for details
3. See [Troubleshooting](./TESTING_GUIDE.md#troubleshooting)
4. Create an issue on GitHub

## 🎓 Learning Path

**Beginner:**
1. Read [Quick Reference](./QUICK_REFERENCE.md)
2. Try `test-fast` and `test-ci` scripts
3. Read [Testing Guide](./TESTING_GUIDE.md) sections as needed

**Intermediate:**
1. Understand [Test Optimization](./TEST_OPTIMIZATION.md)
2. Learn about parallel execution
3. Explore advanced script options

**Advanced:**
1. Study [Parallel Testing Summary](./PARALLEL_TESTING_SUMMARY.md)
2. Optimize slow tests
3. Contribute to test infrastructure

## 📝 Contributing

When updating test documentation:
1. Update relevant guide first
2. Update [Quick Reference](./QUICK_REFERENCE.md) if needed
3. Add entry to [Changelog](./CHANGELOG.md)
4. Update this README if structure changes

## 🔗 Related Documentation

- [Scripts README](../../scripts/README.md) - All available scripts
- [AGENTS.md](../../AGENTS.md) - AI agent instructions
- [Contributing Guide](../development/CONTRIBUTING.md) - Development workflow

---

**Last Updated:** 2026-05-10
**Version:** 1.0.0
