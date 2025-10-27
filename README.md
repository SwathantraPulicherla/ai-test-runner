# AI Test Runner

Compiles, executes, and provides coverage reports for AI-generated C unit tests. This tool automatically finds tests that compile successfully (marked with `compiles_yes` in verification reports) and builds a complete test suite with coverage analysis.

## Features

- 🔍 **Automatic Test Discovery**: Scans `tests/verification_report/` for `compiles_yes` files
- 🔨 **CMake Build System**: Sets up proper build environment with coverage flags
- 🧪 **Test Execution**: Runs all compiled tests and captures results
- 📊 **Coverage Reports**: Generates LCOV coverage reports with HTML output
- 🏗️ **Unity Integration**: Works seamlessly with Unity testing framework
- 📋 **Detailed Reporting**: Comprehensive test execution summaries

## Prerequisites

- **Python 3.8+**
- **CMake** (build system)
- **Make** (build tool)
- **GCC/Clang** (C compiler)
- **LCOV** (coverage reporting - optional but recommended)

### Installing Dependencies

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install cmake build-essential lcov
```

**macOS:**
```bash
brew install cmake lcov
```

**Windows:**
```bash
# Install Visual Studio Build Tools or MinGW
# Install CMake from https://cmake.org/download/
# Install LCOV from https://github.com/linux-test-project/lcov
```

## Installation

### From Source
```bash
git clone https://github.com/your-org/ai-test-runner.git
cd ai-test-runner
pip install -e .
```

## Usage

### Basic Usage
```bash
ai-test-runner
```

### Command Line Options

- `--repo-path PATH`: Path to the C repository (default: current directory)
- `--output DIR`: Output/build directory (default: build)
- `--verbose, -v`: Enable verbose output
- `--version`: Show version information

### Examples

**Run tests in current directory:**
```bash
ai-test-runner
```

**Run tests for specific repository:**
```bash
ai-test-runner --repo-path /path/to/c/project
```

**Run with custom build directory:**
```bash
ai-test-runner --output build/debug
```

**Verbose output:**
```bash
ai-test-runner --verbose
```

## How It Works

1. **Discovery Phase**: Scans `tests/verification_report/` for files ending with `compiles_yes.txt`
2. **Setup Phase**: Copies source files, test files, and Unity framework to build directory
3. **Build Phase**: Creates CMakeLists.txt and builds all tests with coverage flags
4. **Execution Phase**: Runs all compiled test executables
5. **Coverage Phase**: Generates LCOV coverage reports
6. **Reporting Phase**: Displays comprehensive test results and coverage summary

## Project Structure

Your AI-generated test repository should look like this:

```
your-c-project/
├── src/
│   ├── module1.c
│   ├── module2.c
│   └── module1.h
├── tests/
│   ├── test_module1.c      # AI-generated tests
│   ├── test_module2.c      # AI-generated tests
│   └── verification_report/
│       ├── test_module1_compiles_yes.txt
│       └── test_module2_compiles_yes.txt
└── unity/                  # Unity framework
```

After running `ai-test-runner`, you'll get:

```
your-c-project/
├── build/                  # ← Created by ai-test-runner
│   ├── CMakeLists.txt      # Build configuration
│   ├── src/               # Copied source files
│   ├── tests/             # Copied test files
│   ├── unity/             # Unity framework
│   ├── test_module1       # Compiled test executable
│   ├── test_module2       # Compiled test executable
│   └── coverage_html/     # Coverage report
│       └── index.html     # HTML coverage report
```

## Test Execution Results

The tool provides detailed execution results:

```
TEST EXECUTION SUMMARY
============================================================
Total tests run: 3
Tests passed: 2
Tests failed: 1

Failed tests:
  ❌ test_module1
     Error: Test timeout or assertion failure

Build directory: /path/to/project/build
Coverage report: /path/to/project/build/coverage_html/index.html
```

## Coverage Reports

When LCOV is available, the tool generates:
- **coverage.info**: Raw coverage data
- **coverage_source.info**: Filtered coverage for source files only
- **coverage_html/**: HTML coverage report with line-by-line coverage

## Integration with AI Test Generator

This tool is designed to work seamlessly with the [AI C Test Generator](https://github.com/your-org/ai-c-test-generator):

1. **Generate tests** with AI C Test Generator
2. **Validate compilation** (creates `compiles_yes` reports)
3. **Run and cover** tests with AI Test Runner

## Workflow Example

```bash
# 1. Generate AI tests
ai-c-testgen

# 2. Run and test the generated code
ai-test-runner

# 3. View coverage report
# Open build/coverage_html/index.html in your browser
```

## Troubleshooting

### "No compilable tests found"
- Run `ai-c-testgen` first to generate tests
- Check that verification reports exist in `tests/verification_report/`
- Ensure reports have `compiles_yes` in the filename

### "CMake not found"
- Install CMake: `sudo apt-get install cmake`
- Ensure CMake is in your PATH

### "Build failed"
- Check that source files exist in `src/` directory
- Ensure Unity framework is available
- Review build errors in the output

### "Coverage generation failed"
- Install LCOV: `sudo apt-get install lcov`
- Coverage reports are optional - tests will still run without LCOV

### "Test execution failed"
- Check test output for assertion failures
- Review generated test code for logical errors
- Ensure stub functions are properly implemented

## Development

### Setting up for Development
```bash
git clone https://github.com/your-org/ai-test-runner.git
cd ai-test-runner
pip install -e ".[dev]"
```

### Running Tests
```bash
pytest
```

### Building Distribution
```bash
python -m build
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Related Tools

- [AI C Test Generator](https://github.com/your-org/ai-c-test-generator) - Generates the tests that this tool runs
- [Unity Testing Framework](http://www.throwtheswitch.org/unity) - Unit testing framework for C
- [LCOV](http://ltp.sourceforge.net/coverage/lcov.php) - Coverage reporting tool