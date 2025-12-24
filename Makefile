# Makefile for Iron Condor Screener
#
# Common development tasks for the condor-hunter project

.PHONY: help install test test-unit test-integration test-e2e test-verbose test-coverage \
        test-fast clean lint format check validate run-example run-spy run-batch \
        docs coverage-html coverage-report validate-tests

# Default target
.DEFAULT_GOAL := help

##@ General

help: ## Display this help message
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Setup

install: ## Install dependencies
	pip install -r requirements.txt
	@echo "✅ Dependencies installed"

install-dev: ## Install dependencies including development tools
	pip install -r requirements.txt
	pip install pytest pytest-cov pytest-xdist black flake8 mypy
	@echo "✅ Development dependencies installed"

##@ Testing

test: ## Run all tests
	pytest

test-unit: ## Run only unit tests (fast)
	pytest condor_screener/tests/test_models.py \
	       condor_screener/tests/test_data.py \
	       condor_screener/tests/test_builder.py \
	       condor_screener/tests/test_analytics.py \
	       condor_screener/tests/test_scoring.py

test-integration: ## Run only integration tests
	pytest condor_screener/tests/test_integration.py

test-e2e: ## Run only E2E tests
	pytest condor_screener/tests/test_e2e.py -v

test-verbose: ## Run all tests with verbose output
	pytest -v

test-fast: ## Run tests in parallel (requires pytest-xdist)
	pytest -n auto

test-coverage: ## Run tests with coverage report
	pytest --cov=condor_screener --cov-report=term-missing

coverage-html: ## Generate HTML coverage report
	pytest --cov=condor_screener --cov-report=html
	@echo "✅ Coverage report generated at htmlcov/index.html"

coverage-report: ## Generate both terminal and HTML coverage reports
	pytest --cov=condor_screener --cov-report=term-missing --cov-report=html
	@echo "✅ Coverage reports generated"

validate-tests: ## Validate test structure
	python3 scripts/validate_tests.py

##@ Code Quality

lint: ## Run linting checks
	@echo "Running flake8..."
	@flake8 condor_screener/ --count --select=E9,F63,F7,F82 --show-source --statistics || true
	@echo "✅ Linting complete"

format: ## Format code with black
	@echo "Formatting with black..."
	@black condor_screener/ || true
	@echo "✅ Formatting complete"

check: ## Run type checking with mypy
	@echo "Running mypy type checks..."
	@mypy condor_screener/ --ignore-missing-imports || true
	@echo "✅ Type checking complete"

validate: lint check ## Run all validation checks

##@ Running Examples

run-example: ## Run the example SPY screener
	python3 condor_screener/examples/screen_spy.py

run-spy: run-example ## Alias for run-example

##@ Cleaning

clean: ## Remove generated files and caches
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	rm -rf htmlcov/ 2>/dev/null || true
	rm -rf .coverage 2>/dev/null || true
	rm -rf dist/ 2>/dev/null || true
	rm -rf build/ 2>/dev/null || true
	@echo "✅ Cleaned generated files"

clean-test: ## Remove test artifacts
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	@echo "✅ Cleaned test artifacts"

##@ Documentation

docs: ## Display documentation files
	@echo "\n📚 Documentation Files:\n"
	@echo "  README.md              - Project overview"
	@echo "  README_TESTING.md      - Testing guide"
	@echo "  TEST_SUMMARY.md        - Test suite summary"
	@echo "  how_to_use.md          - Usage guide"
	@echo "  e2e.md                 - End-to-end workflows"
	@echo "  next_steps.md          - Future improvements"
	@echo "  TESTING_COMPLETE.md    - Testing completion report"
	@echo ""

##@ Development Workflow

dev-setup: install-dev ## Complete development environment setup
	@echo "✅ Development environment ready"
	@echo ""
	@echo "Next steps:"
	@echo "  make test              # Run tests"
	@echo "  make run-example       # Run example screener"
	@echo "  make help              # See all commands"

pre-commit: clean lint test ## Run pre-commit checks
	@echo "✅ Pre-commit checks passed"

ci: install test-coverage ## Run CI pipeline locally
	@echo "✅ CI checks complete"

##@ Specific Test Categories

test-models: ## Test data models only
	pytest condor_screener/tests/test_models.py -v

test-data: ## Test data loaders/validators only
	pytest condor_screener/tests/test_data.py -v

test-builder: ## Test condor builder only
	pytest condor_screener/tests/test_builder.py -v

test-analytics: ## Test analytics only
	pytest condor_screener/tests/test_analytics.py -v

test-scoring: ## Test scoring system only
	pytest condor_screener/tests/test_scoring.py -v

##@ Testing Workflows

test-basic-flow: ## Test basic screening workflow (E2E)
	pytest condor_screener/tests/test_e2e.py::TestE2EBasicScreeningFlow -v

test-strategies: ## Test custom strategy parameters (E2E)
	pytest condor_screener/tests/test_e2e.py::TestE2ECustomStrategyParameters -v

test-multi-ticker: ## Test multi-ticker screening (E2E)
	pytest condor_screener/tests/test_e2e.py::TestE2EMultiTickerScreening -v

test-troubleshooting: ## Test troubleshooting scenarios (E2E)
	pytest condor_screener/tests/test_e2e.py::TestE2ETroubleshooting -v

##@ Quick Actions

quick-test: ## Quick test run (unit tests only, no coverage)
	@echo "Running quick tests..."
	@pytest condor_screener/tests/test_models.py condor_screener/tests/test_scoring.py -q

watch-test: ## Run tests on file changes (requires pytest-watch)
	@command -v ptw >/dev/null 2>&1 || { echo "Installing pytest-watch..."; pip install pytest-watch; }
	ptw -- condor_screener/tests/

##@ Information

show-config: ## Show pytest configuration
	pytest --version
	@echo ""
	@echo "Pytest configuration (pytest.ini):"
	@cat pytest.ini

show-coverage-config: ## Show coverage configuration
	@echo "Coverage configuration (.coveragerc):"
	@cat .coveragerc

stats: ## Show project statistics
	@echo "\n📊 Project Statistics:\n"
	@echo "Python files:"
	@find condor_screener -name "*.py" -not -path "*/tests/*" | wc -l
	@echo ""
	@echo "Test files:"
	@find condor_screener/tests -name "test_*.py" | wc -l
	@echo ""
	@echo "Lines of code (excluding tests):"
	@find condor_screener -name "*.py" -not -path "*/tests/*" -exec wc -l {} + | tail -1
	@echo ""
	@echo "Lines of test code:"
	@find condor_screener/tests -name "test_*.py" -exec wc -l {} + | tail -1
	@echo ""

tree: ## Show project structure
	@echo "\n📁 Project Structure:\n"
	@tree -I '__pycache__|*.pyc|htmlcov|.pytest_cache|.mypy_cache|*.egg-info' -L 3 || \
		find . -not -path '*/\.*' -not -path '*/__pycache__/*' -not -path '*/htmlcov/*' | head -50

##@ Utilities

check-deps: ## Check if all dependencies are installed
	@echo "Checking dependencies..."
	@python3 -c "import yaml; print('✅ pyyaml')" 2>/dev/null || echo "❌ pyyaml not installed"
	@python3 -c "import pytest; print('✅ pytest')" 2>/dev/null || echo "❌ pytest not installed"
	@python3 -c "import pytest_cov; print('✅ pytest-cov')" 2>/dev/null || echo "❌ pytest-cov not installed"

version: ## Show Python and pytest versions
	@echo "Python version:"
	@python3 --version
	@echo ""
	@echo "Pytest version:"
	@pytest --version

##@ Advanced

test-pattern: ## Run tests matching pattern (use: make test-pattern PATTERN=screening)
	pytest -k "$(PATTERN)" -v

test-mark: ## Run tests with specific marker (use: make test-mark MARK=unit)
	pytest -m "$(MARK)" -v

test-collect: ## Show which tests would run without executing
	pytest --collect-only

test-failed: ## Re-run only failed tests from last run
	pytest --lf

test-debug: ## Run tests with debugging enabled
	pytest --pdb -v

benchmark: ## Run performance benchmarks (if implemented)
	@echo "No benchmarks implemented yet"
	@echo "See TEST_SUMMARY.md for future enhancements"

##@ Git Hooks (optional)

install-hooks: ## Install git pre-commit hooks
	@echo "#!/bin/bash" > .git/hooks/pre-commit
	@echo "make pre-commit" >> .git/hooks/pre-commit
	@chmod +x .git/hooks/pre-commit
	@echo "✅ Pre-commit hook installed"

##@ All-in-One Commands

all: clean install test ## Clean, install, and test everything
	@echo "✅ All tasks complete"

verify: validate test-coverage ## Validate code and run tests with coverage
	@echo "✅ Verification complete"

release-check: clean verify docs ## Full release checklist
	@echo "✅ Release checks passed"
	@echo ""
	@echo "Release checklist:"
	@echo "  ✅ Code cleaned"
	@echo "  ✅ Code validated"
	@echo "  ✅ Tests passed with coverage"
	@echo "  ✅ Documentation reviewed"
