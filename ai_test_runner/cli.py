#!/usr/bin/env python3
"""
AI Test Runner - Compiles, executes, and provides coverage for AI-generated tests
"""

import os
import sys
import argparse
import shutil
import subprocess
from pathlib import Path
import glob
import re

# Import DependencyAnalyzer from ai-c-test-generator
sys.path.append(str(Path(__file__).parent.parent.parent / "ai-c-test-generator"))
from ai_c_test_generator.analyzer import DependencyAnalyzer


class AITestRunner:
    """AI Test Runner - Builds, executes, and covers AI-generated tests"""

    def __init__(self, repo_path: str, output_dir: str = "build"):
        self.repo_path = Path(repo_path).resolve()
        self.output_dir = self.repo_path / output_dir
        self.tests_dir = self.repo_path / "tests"
        self.verification_dir = self.tests_dir / "verification_report"
        self.test_reports_dir = self.tests_dir / "test_reports"
        self.source_dir = self.repo_path / "src"

        # Initialize dependency analyzer
        self.analyzer = DependencyAnalyzer(str(self.repo_path))

        # Create output directory
        self.output_dir.mkdir(exist_ok=True)
        # Create test reports directory
        self.test_reports_dir.mkdir(parents=True, exist_ok=True)

    def get_stubbed_functions_in_test(self, test_file_path: str) -> set:
        """Detect function stubs in a test file by parsing function definitions"""
        stubbed_functions = set()
        try:
            with open(test_file_path, 'r') as f:
                content = f.read()

            # Match function definitions like: float raw_to_celsius(int raw) {
            # Capture the function name (second word), not the return type
            matches = re.findall(r'\b\w+\s+(\w+)\s*\([^)]*\)\s*{', content)
            stubbed_functions = set(matches)

            # Remove test functions (they start with "test_")
            stubbed_functions = {func for func in stubbed_functions if not func.startswith('test_')}

        except Exception as e:
            print(f"Warning: Could not parse stubs from {test_file_path}: {e}")

        return stubbed_functions

    def find_compilable_tests(self):
        """Find test files that have compiles_yes in verification reports"""
        compilable_tests = []

        if not self.verification_dir.exists():
            print(f"❌ Verification report directory not found: {self.verification_dir}")
            return compilable_tests

        # Find all compiles_yes files
        for report_file in self.verification_dir.glob("*compiles_yes.txt"):
            # Extract test filename from report filename
            # Format: test_filename_compiles_yes.txt -> test_filename.c
            base_name = report_file.stem.replace("_compiles_yes", "")
            test_file = self.tests_dir / f"{base_name}.c"

            if test_file.exists():
                compilable_tests.append(test_file)
                print(f"✅ Found compilable test: {test_file.name}")
            else:
                print(f"⚠️  Test file not found: {test_file.name}")

        return compilable_tests

    def copy_unity_framework(self):
        """Copy or download Unity framework"""
        unity_dest = self.output_dir / "unity"

        # First try to copy from reference location
        unity_source = self.repo_path.parent / "ai-test-gemini-CLI" / "unity"
        if unity_source.exists() and any(unity_source.rglob("*.c")):
            if unity_dest.exists():
                try:
                    shutil.rmtree(unity_dest)
                except (OSError, PermissionError):
                    print(f"⚠️  Could not remove existing unity directory: {unity_dest}")
            shutil.copytree(unity_source, unity_dest)
            print("✅ Copied Unity framework from reference")
            return

        # If not available, download Unity
        print("📥 Downloading Unity framework...")
        import urllib.request
        import zipfile
        import tempfile

        try:
            # Download Unity from GitHub
            unity_url = "https://github.com/ThrowTheSwitch/Unity/archive/refs/heads/master.zip"
            with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp_zip:
                urllib.request.urlretrieve(unity_url, temp_zip.name)

                # Extract Unity
                with zipfile.ZipFile(temp_zip.name, 'r') as zip_ref:
                    # Extract only the src directory
                    for member in zip_ref.namelist():
                        if member.startswith('Unity-master/src/'):
                            # Remove the Unity-master/src/ prefix
                            target_path = member.replace('Unity-master/src/', 'src/')
                            if target_path.endswith('/'):
                                (unity_dest / target_path).mkdir(parents=True, exist_ok=True)
                            else:
                                zip_ref.extract(member, unity_dest.parent / "temp_unity")
                                source_file = unity_dest.parent / "temp_unity" / member
                                target_file = unity_dest / target_path
                                target_file.parent.mkdir(parents=True, exist_ok=True)
                                shutil.move(source_file, target_file)

                # Clean up
                import os
                os.unlink(temp_zip.name)
                temp_dir = unity_dest.parent / "temp_unity"
                if temp_dir.exists():
                    shutil.rmtree(temp_dir)

            print("✅ Downloaded Unity framework")

        except Exception as e:
            print(f"❌ Failed to download Unity: {e}")
            print("⚠️  Unity framework not available, tests may not compile")

    def create_cmake_lists(self, test_files):
        cmake_content = "cmake_minimum_required(VERSION 3.10)\n"
        cmake_content += "project(Tests C)\n\n"
        cmake_content += "set(CMAKE_C_STANDARD 99)\n"
        cmake_content += "add_definitions(-DUNIT_TEST)\n\n"
        # Add coverage compilation flags
        cmake_content += "set(CMAKE_C_FLAGS \"${CMAKE_C_FLAGS} --coverage\")\n"
        cmake_content += "set(CMAKE_EXE_LINKER_FLAGS \"${CMAKE_EXE_LINKER_FLAGS} --coverage\")\n\n"
        cmake_content += "include_directories(unity/src)\n"
        cmake_content += "include_directories(src)\n\n"

        # Add Unity source file
        cmake_content += "add_library(unity unity/src/unity.c)\n\n"

        source_files = [f for f in os.listdir(os.path.join(self.output_dir, 'src')) if f.endswith('.c')]
        
        for test_file in test_files:
            test_name = os.path.splitext(os.path.basename(test_file))[0]
            executable_name = test_name

            # --- INTELLIGENT SOURCE FILE SELECTION ---
            # Determine the primary source file being tested (e.g., test_main.c -> main.c)
            source_under_test = test_name.replace('test_', '') + '.c'

            # Find all functions stubbed in the test file
            stubbed_functions = self._find_stubbed_functions(os.path.join(self.output_dir, 'tests', test_file))
            
            # Determine which source files provide the stubbed functions
            source_files_with_stubs = set()
            for func in stubbed_functions:
                for src_file in source_files:
                    # A simple check, can be improved with more robust parsing
                    with open(os.path.join(self.output_dir, 'src', src_file), 'r', errors='ignore') as f:
                        if func in f.read():
                            source_files_with_stubs.add(src_file)

            # Link only the necessary source files: all sources MINUS the ones that are stubbed
            test_sources = [os.path.join('src', s) for s in source_files if s not in source_files_with_stubs]
            
            # Always include the source file being tested (unless it's stubbed, which it shouldn't be)
            primary_source = os.path.join('src', source_under_test)
            if primary_source not in test_sources and os.path.exists(os.path.join(self.output_dir, 'src', source_under_test)):
                test_sources.append(primary_source)


            # Convert backslashes to forward slashes for CMake compatibility
            test_sources = [src.replace('\\', '/') for src in test_sources]
            test_file_basename = os.path.basename(test_file).replace('\\', '/')
            cmake_content += f"add_executable({executable_name} tests/{test_file_basename} {' '.join(test_sources)})\n"
            cmake_content += f"target_link_libraries({executable_name} unity)\n\n"

        with open(os.path.join(self.output_dir, 'CMakeLists.txt'), 'w') as f:
            f.write(cmake_content)
        print(f"Created CMakeLists.txt with {len(test_files)} test targets")

    def _find_stubbed_functions(self, test_file_path):
        """Finds function names that are defined as stubs in a test file."""
        stubs = set()
        try:
            with open(test_file_path, 'r', errors='ignore') as f:
                content = f.read()
                # Regex to find function definitions that are not test_ or setUp/tearDown
                # This matches: word( parameters ){ 
                # The word before ( is the function name
                pattern = re.compile(r'(\w+)\s*\([^)]*\)\s*{', re.MULTILINE)
                for match in pattern.finditer(content):
                    func_name = match.group(1)
                    if not func_name.startswith(('test_', 'setUp', 'tearDown', 'main')):
                        stubs.add(func_name)
        except FileNotFoundError:
            pass
        return stubs

    def copy_source_files(self):
        """Copy source files to build directory"""
        src_build_dir = self.output_dir / "src"
        src_build_dir.mkdir(exist_ok=True)

        if self.source_dir.exists():
            for src_file in self.source_dir.glob("*.c"):
                shutil.copy2(src_file, src_build_dir)
                print(f"📋 Copied source: {src_file.name}")

            for header_file in self.source_dir.glob("*.h"):
                shutil.copy2(header_file, src_build_dir)
                print(f"📋 Copied header: {header_file.name}")
        else:
            print(f"⚠️  Source directory not found: {self.source_dir}")

    def copy_test_files(self, test_files):
        """Copy test files to build directory"""
        tests_build_dir = self.output_dir / "tests"
        tests_build_dir.mkdir(exist_ok=True)

        for test_file in test_files:
            shutil.copy2(test_file, tests_build_dir)
            print(f"📋 Copied test: {test_file.name}")

    def build_tests(self):
        """Build the tests using CMake"""
        print("🔨 Building tests...")

        try:
            # Configure with CMake (CMakeLists.txt is in the build directory)
            result = subprocess.run(
                ["cmake", "."],
                cwd=self.output_dir,
                capture_output=True,
                text=True,
                check=True
            )
            print("✅ CMake configuration successful")

            # Build with cmake --build (works with any generator)
            result = subprocess.run(
                ["cmake", "--build", "."],
                cwd=self.output_dir,
                capture_output=True,
                text=True,
                check=True
            )
            print("✅ Build successful")

        except subprocess.CalledProcessError as e:
            print(f"❌ Build failed: {e}")
            print(f"STDOUT: {e.stdout}")
            print(f"STDERR: {e.stderr}")
            return False
        except FileNotFoundError:
            print("❌ CMake not found. Please install CMake.")
            return False

        return True

    def run_tests(self):
        """Run the compiled tests"""
        print("🧪 Running tests...")

        test_results = []
        test_executables = [exe for exe in self.output_dir.glob("*test*") 
                           if exe.is_file() and exe.suffix in ['.exe', ''] and 'CTest' not in exe.name]

        if not test_executables:
            print("❌ No test executables found")
            return test_results

        for exe in test_executables:
            if exe.is_file() and os.access(exe, os.X_OK):
                print(f"   Running {exe.name}...")
                try:
                    result = subprocess.run(
                        [str(exe)],
                        cwd=self.output_dir,
                        capture_output=True,
                        text=True,
                        timeout=30
                    )

                    # Parse Unity test output to count individual tests
                    individual_tests = 0
                    individual_passed = 0
                    individual_failed = 0

                    for line in result.stdout.split('\n'):
                        line = line.strip()
                        if ':PASS' in line:
                            individual_tests += 1
                            individual_passed += 1
                        elif ':FAIL' in line:
                            individual_tests += 1
                            individual_failed += 1
                        elif line.endswith('Tests') and 'Failures' in line:
                            # Parse summary line like "5 Tests 0 Failures 0 Ignored"
                            parts = line.split()
                            if len(parts) >= 3:
                                try:
                                    individual_tests = int(parts[0])
                                    individual_failed = int(parts[2])
                                    individual_passed = individual_tests - individual_failed
                                except ValueError:
                                    pass

                    success = result.returncode == 0
                    test_results.append({
                        'name': exe.name,
                        'success': success,
                        'output': result.stdout,
                        'errors': result.stderr,
                        'returncode': result.returncode,
                        'individual_tests': individual_tests,
                        'individual_passed': individual_passed,
                        'individual_failed': individual_failed
                    })

                    status = "✅" if success else "❌"
                    if individual_tests > 0:
                        print(f"   {status} {exe.name} ({individual_passed}/{individual_tests} tests passed)")
                    else:
                        print(f"   {status} {exe.name} (exit code: {result.returncode})")

                except subprocess.TimeoutExpired:
                    test_results.append({
                        'name': exe.name,
                        'success': False,
                        'output': '',
                        'errors': 'Test timed out',
                        'returncode': -1,
                        'individual_tests': 0,
                        'individual_passed': 0,
                        'individual_failed': 0
                    })
                    print(f"   ⏰ {exe.name} timed out")

                except Exception as e:
                    test_results.append({
                        'name': exe.name,
                        'success': False,
                        'output': '',
                        'errors': str(e),
                        'returncode': -1,
                        'individual_tests': 0,
                        'individual_passed': 0,
                        'individual_failed': 0
                    })
                    print(f"   ❌ {exe.name} failed: {e}")

        return test_results

    def generate_test_reports(self, test_results):
        """Generate individual test reports for each test executable"""
        print(f"📝 Generating individual test reports in {self.test_reports_dir}...")

        # Clean old reports
        for old_report in self.test_reports_dir.glob("*_report.txt"):
            old_report.unlink()

        for result in test_results:
            report_file = self.test_reports_dir / f"{result['name']}_report.txt"

            with open(report_file, 'w', encoding='utf-8') as f:
                f.write("=" * 60 + "\n")
                f.write(f"TEST REPORT: {result['name']}\n")
                f.write("=" * 60 + "\n\n")

                f.write("EXECUTION SUMMARY\n")
                f.write("-" * 20 + "\n")
                f.write(f"Test Executable: {result['name']}\n")
                f.write(f"Exit Code: {result['returncode']}\n")
                f.write(f"Overall Status: {'PASSED' if result['success'] else 'FAILED'}\n")
                f.write(f"Individual Tests Run: {result['individual_tests']}\n")
                f.write(f"Individual Tests Passed: {result['individual_passed']}\n")
                f.write(f"Individual Tests Failed: {result['individual_failed']}\n\n")

                if result['errors']:
                    f.write("ERRORS\n")
                    f.write("-" * 10 + "\n")
                    f.write(f"{result['errors']}\n\n")

                f.write("DETAILED OUTPUT\n")
                f.write("-" * 20 + "\n")
                if result['output']:
                    f.write(result['output'])
                else:
                    f.write("(No output captured)\n")

                f.write("\n" + "=" * 60 + "\n")

            print(f"   📄 Generated report: {report_file.name}")

    def generate_coverage(self):
        """Generate coverage reports using lcov and print a summary"""
        print("📊 Generating coverage reports...")

        # Clean old coverage files
        coverage_info = self.output_dir / "coverage.info"
        coverage_source_info = self.output_dir / "coverage_source.info"
        coverage_html_dir = self.tests_dir / "coverage_reports"

        if coverage_info.exists():
            coverage_info.unlink()
        if coverage_source_info.exists():
            coverage_source_info.unlink()
        if coverage_html_dir.exists():
            shutil.rmtree(coverage_html_dir)

        try:
            # Capture coverage data
            subprocess.run(
                ["lcov", "--capture", "--directory", ".", "--output-file", "coverage.info", "--ignore-errors", "unused"],
                cwd=self.output_dir, capture_output=True, text=True, check=True
            )

            # Extract coverage for source files only
            subprocess.run(
                ["lcov", "--extract", "coverage.info", "src/*.c", "--output-file", "coverage_source.info", "--ignore-errors", "unused,empty"],
                cwd=self.output_dir, capture_output=True, text=True, check=True
            )

            # Generate HTML report
            coverage_reports_path = self.tests_dir / "coverage_reports"
            subprocess.run(
                ["genhtml", "coverage_source.info", "--output-directory", str(coverage_reports_path)],
                cwd=self.output_dir, capture_output=True, text=True, check=True
            )

            # Generate console summary
            summary_result = subprocess.run(
                ["lcov", "--list", "coverage_source.info"],
                cwd=self.output_dir, capture_output=True, text=True, check=True
            )

            print(f"✅ Coverage report generated: {coverage_html_dir}")
            self.print_coverage_summary(summary_result.stdout)
            return True

        except subprocess.CalledProcessError as e:
            print(f"❌ Coverage generation failed: {e.stderr}")
            print("Note: Install lcov for coverage reports: sudo apt-get install lcov")
            return False
        except FileNotFoundError:
            print("❌ lcov not found. Install with: sudo apt-get install lcov")
            return False

    def print_coverage_summary(self, lcov_output):
        """Parse lcov output and print a summary table"""
        print("\nCOVERAGE SUMMARY")
        print("=" * 60)
        
        lines = lcov_output.strip().split('\n')
        
        total_lines = 0
        total_lines_hit = 0
        
        # Header
        print(f"{'File':<30} | {'Lines':>10} | {'Coverage':>10}")
        print("-" * 60)

        for line in lines:
            if "summary" in line:
                continue
            parts = line.split('|')
            if len(parts) >= 3:
                try:
                    file_name = parts[0].strip()
                    coverage_percent = float(parts[1].strip().split('%')[0])
                    lines_part = parts[2].strip()
                    
                    lines_hit = int(lines_part.split('/')[0])
                    lines_total = int(lines_part.split('/')[1])
                    
                    total_lines += lines_total
                    total_lines_hit += lines_hit
                    
                    print(f"{file_name:<30} | {f'{lines_hit}/{lines_total}':>10} | {f'{coverage_percent:.1f}%':>10}")
                except (ValueError, IndexError):
                    continue
        
        print("-" * 60)
        if total_lines > 0:
            total_coverage = (total_lines_hit / total_lines) * 100
            print(f"{'Total':<30} | {f'{total_lines_hit}/{total_lines}':>10} | {f'{total_coverage:.1f}%':>10}")
        print("=" * 60)

    def print_summary(self, test_results):
        """Print test execution summary"""
        print(f"\n{'='*60}")
        print("TEST EXECUTION SUMMARY")
        print(f"{'='*60}")

        total_executables = len(test_results)
        passed_executables = sum(1 for r in test_results if r['success'])

        # Count individual test functions
        total_individual_tests = sum(r.get('individual_tests', 0) for r in test_results)
        total_individual_passed = sum(r.get('individual_passed', 0) for r in test_results)
        total_individual_failed = sum(r.get('individual_failed', 0) for r in test_results)

        print(f"Test executables run: {total_executables}")
        print(f"Test executables passed: {passed_executables}")
        print(f"Test executables failed: {total_executables - passed_executables}")
        print()
        print(f"Individual test functions run: {total_individual_tests}")
        print(f"Individual test functions passed: {total_individual_passed}")
        print(f"Individual test functions failed: {total_individual_failed}")

        if total_executables != passed_executables:
            print(f"\nFailed test executables:")
            for result in test_results:
                if not result['success']:
                    print(f"  ❌ {result['name']}")
                    if result['errors']:
                        print(f"     Error: {result['errors']}")

        print(f"\nBuild directory: {self.output_dir.relative_to(self.repo_path)}")
        coverage_dir = self.tests_dir / "coverage_reports" / "index.html"
        if coverage_dir.exists():
            print(f"Coverage report: {coverage_dir.relative_to(self.repo_path)}")

    def find_test_files(self):
        """Find all test files, excluding test_main.c"""
        test_files = []
        if os.path.exists(os.path.join(self.output_dir, 'tests')):
            for file in os.listdir(os.path.join(self.output_dir, 'tests')):
                if file.endswith('.c') and file.startswith('test_'):
                    # Skip test_main.c as main.c is not unit tested
                    if file == 'test_main.c':
                        continue
                    test_files.append(file)
        return test_files

    def run(self):
        """Main execution flow"""
        print("🚀 AI Test Runner")
        print(f"   Repository: {self.repo_path}")
        print(f"   Output dir: {self.output_dir}")
        print()

        # Find compilable tests
        compilable_tests = self.find_compilable_tests()
        if not compilable_tests:
            print("❌ No compilable tests found. Run AI test generation first.")
            return False

        # Set up build environment
        self.copy_unity_framework()
        self.copy_source_files()
        self.copy_test_files(compilable_tests)
        self.create_cmake_lists(compilable_tests)

        # Build tests
        if not self.build_tests():
            return False

        # Run tests
        test_results = self.run_tests()

        # Generate individual test reports
        self.generate_test_reports(test_results)

        # Generate coverage
        self.generate_coverage()

        # Print summary
        self.print_summary(test_results)

        # Calculate success based on individual test functions
        total_individual_tests = sum(r.get('individual_tests', 0) for r in test_results)
        total_individual_passed = sum(r.get('individual_passed', 0) for r in test_results)

        if total_individual_tests > 0:
            print(f"\n🎉 COMPLETED: {total_individual_passed}/{total_individual_tests} individual test functions passed")
        else:
            # Fallback to executable count if individual counts not available
            success_count = sum(1 for r in test_results if r['success'])
            print(f"\n🎉 COMPLETED: {success_count}/{len(test_results)} test executables passed")

        return total_individual_passed == total_individual_tests if total_individual_tests > 0 else success_count == len(test_results)


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(
        description="AI Test Runner - Compiles, executes, and provides coverage for AI-generated tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run tests for current repository
  ai-test-runner

  # Run tests for specific repository
  ai-test-runner --repo-path /path/to/c/project

  # Run tests with custom build directory
  ai-test-runner --output build/debug
        """
    )

    parser.add_argument(
        '--repo-path',
        type=str,
        default='.',
        help='Path to the C repository (default: current directory)'
    )

    parser.add_argument(
        '--output',
        type=str,
        default='build',
        help='Output/build directory (default: build)'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )

    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s 1.0.0'
    )

    args = parser.parse_args()

    # Check for required tools
    required_tools = ['cmake']
    missing_tools = []

    for tool in required_tools:
        if not shutil.which(tool):
            missing_tools.append(tool)

    if missing_tools:
        print(f"❌ Missing required tools: {', '.join(missing_tools)}")
        print("Please install build tools:")
        print("  Ubuntu/Debian: sudo apt-get install cmake build-essential")
        print("  macOS: brew install cmake")
        print("  Windows: Install CMake (includes Ninja generator)")
        return 1

    # Run the test runner
    runner = AITestRunner(args.repo_path, args.output)
    success = runner.run()

    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())