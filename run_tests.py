#!/usr/bin/env python3
"""Test runner for Open FinOps Stack."""

import subprocess
import sys
from pathlib import Path


def run_command(cmd, description):
    """Run a command and report results."""
    print(f"\n🔄 {description}")
    print(f"Command: {' '.join(cmd)}")
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"✅ {description} - PASSED")
        if result.stdout.strip():
            print(result.stdout)
    else:
        print(f"❌ {description} - FAILED")
        if result.stderr.strip():
            print("STDERR:", result.stderr)
        if result.stdout.strip():
            print("STDOUT:", result.stdout)
    
    return result.returncode == 0


def main():
    """Main test runner."""
    print("🧪 Open FinOps Stack Test Runner")
    print("=" * 50)
    
    # Check if we're in a virtual environment
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("⚠️  Warning: Not running in a virtual environment")
        print("   Consider running: python -m venv venv && source venv/bin/activate")
    
    all_passed = True
    
    # Generate sample test data
    print("\n📊 Generating sample test data...")
    try:
        # Generate FOCUS-compliant sample data
        from tests.data.generate_sample_data import create_test_s3_structure
        
        sample_path = Path("./tmp/test-data-sample")
        sample_path.mkdir(exist_ok=True)
        
        create_test_s3_structure(
            base_path=sample_path,
            bucket_name="sample-bucket",
            prefix="sample-reports",
            export_name="sample-export",
            billing_periods=["2024-01", "2024-02", "2024-03"],
            cur_version="v1",
            num_records_per_period=10
        )
        print("✅ FOCUS sample data generated")
        
        # Generate AWS CUR sample data
        from tests.data.generate_aws_cur_data import create_aws_cur_test_structure
        
        aws_sample_path = Path("./tmp/test-aws-cur-sample")
        aws_sample_path.mkdir(exist_ok=True)
        
        create_aws_cur_test_structure(
            base_path=aws_sample_path,
            bucket_name="sample-cur-bucket",
            prefix="cur-reports",
            export_name="sample-cur-export",
            billing_periods=["2024-01", "2024-02", "2024-03"],
            cur_version="v1",
            num_records_per_period=50
        )
        print("✅ AWS CUR sample data generated")
        
    except Exception as e:
        print(f"❌ Failed to generate sample data: {e}")
        all_passed = False
    
    # Run unit tests
    if not run_command(
        ["python3", "-m", "pytest", "tests/unit/", "-v", "--tb=short"],
        "Running unit tests"
    ):
        all_passed = False
    
    # Run integration tests
    if not run_command(
        ["python3", "-m", "pytest", "tests/integration/", "-v", "--tb=short"],
        "Running integration tests"
    ):
        all_passed = False
    
    # Run all tests with coverage (optional)
    if "--coverage" in sys.argv:
        if not run_command(
            ["python3", "-m", "pytest", "--cov=src", "--cov-report=term-missing"],
            "Running tests with coverage"
        ):
            all_passed = False
    
    # Code quality checks (if tools are available)
    if "--quality" in sys.argv:
        # Black formatting check
        run_command(
            ["python3", "-m", "black", "--check", "src/", "tests/"],
            "Checking code formatting (black)"
        )
        
        # Ruff linting
        run_command(
            ["python3", "-m", "ruff", "check", "src/", "tests/"],
            "Running linter (ruff)"
        )
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 All tests passed!")
        return 0
    else:
        print("💥 Some tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())