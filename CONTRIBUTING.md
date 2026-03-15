# Contributing to OM-1 Stacking Pipeline

Thank you for your interest in contributing! 🎉

## 🤝 How to Contribute

### Reporting Bugs

1. Check [existing issues](https://github.com/okuemmel/om1-stacking-pipeline/issues)
2. Create new issue with:
   - Clear title and description
   - Steps to reproduce
   - Expected vs actual behavior
   - Screenshots if applicable
   - System info (macOS version, Python version)

### Suggesting Features

1. Open an issue with `[Feature Request]` prefix
2. Describe the feature and use case
3. Explain why it would be useful

### Pull Requests

1. **Fork** the repository
2. **Create branch** from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make changes** with clear commits:
   ```bash
   git commit -m "Add: feature description"
   ```
4. **Test thoroughly**:
   ```bash
   python3 macro_stacking_web_v4.1.py
   ./build.sh
   ```
5. **Push** to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```
6. **Open Pull Request** with description of changes

## 📝 Code Style

- Follow PEP 8 for Python code
- Use meaningful variable names
- Add comments for complex logic
- Update documentation for new features

## 🧪 Testing

Before submitting PR:

```bash
# Test web interface
python3 macro_stacking_web_v4.1.py

# Test app build
./build.sh
open "dist/OM-1 Stacking Pipeline.app"

# Test with sample images
# (Add test images to test_images/ folder)
```

## 📚 Documentation

- Update README.md for user-facing changes
- Update BUILD.md for build process changes
- Add docstrings to new functions
- Update CHANGELOG.md

## 🎯 Areas for Contribution

### High Priority
- [ ] Windows/Linux support
- [ ] Additional stacking engines (focus-stack fallback)
- [ ] Batch processing API
- [ ] GPU acceleration
- [ ] Unit tests

### Medium Priority
- [ ] Docker container
- [ ] Cloud 