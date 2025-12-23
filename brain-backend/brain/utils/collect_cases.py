# Copyright (C) 2021 - 2025, Shanghai Yunsilicon Technology Co., Ltd.
# All rights reserved.

import os
import subprocess
import fnmatch
import logging

EXCLUDE_DIRS = [
    "products/beryl_chassis/1p1",
    "products/test/test_pytest_exit"
]
LOG = logging.getLogger(__name__)


def setup_pythonpath(root_dir):
    """Set up PYTHONPATH"""
    new_path = f"{root_dir}:"
    os.environ['PYTHONPATH'] = new_path
    LOG.debug(f"PYTHONPATH set to {new_path}")


def collect_tests_with_detailed_report(dirs: list, root_dir):
    """Collect test cases from multiple directories"""
    setup_pythonpath(root_dir)

    parent_dirs = [
        os.path.join(root_dir, d) if not os.path.isabs(d) else d
        for d in dirs
    ]
    exclude_dirs = [
        os.path.join(root_dir, d) if not os.path.isabs(d) else d
        for d in EXCLUDE_DIRS
    ]

    LOG.info(f"Scanning test directories: {dirs}")
    all_test_dirs = find_all_test_directories(parent_dirs, exclude_dirs)
    LOG.info(f"Found {len(all_test_dirs)} test directories")

    scanned_tests = []

    for test_dir in all_test_dirs:
        if not os.path.exists(test_dir):
            LOG.warning(f"Skipped missing directory: {test_dir}")
            continue

        cmd = ["pytest", "--collect-only", "-q", test_dir, "--env", r'\"\"']
        try:
            result = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=os.environ
            )
            stdout, stderr = result.communicate()

            if result.returncode == 0:
                output = stdout.decode('utf-8')
                tests = parse_pytest_output_improved(output)
                scanned_tests.extend(tests)
                LOG.info(f"Collected {len(tests)} tests from {test_dir}")
            else:
                err = stderr.decode('utf-8').strip().splitlines()[-1:]
                LOG.error(f"Failed to collect tests from {test_dir}: {' '.join(err)}")

        except Exception as e:
            LOG.error(f"Error collecting tests in {test_dir}: {e}")

    scanned_tests = sorted(set(scanned_tests))
    LOG.info(f"Total unique test cases collected: {len(scanned_tests)}")
    return scanned_tests


def find_all_test_directories(parent_dirs, exclude_dirs):
    """Find all directories that contain pytest test files"""
    all_test_dirs = set()

    for parent_dir in parent_dirs:
        if not os.path.exists(parent_dir):
            LOG.warning(f"Parent directory not found: {parent_dir}")
            continue

        for root, dirs, _ in os.walk(parent_dir):
            dirs[:] = [
                d for d in dirs
                if not any(os.path.join(root, d).startswith(ex_dir) for ex_dir in exclude_dirs)
            ]

            if any(root.startswith(ex_dir) for ex_dir in exclude_dirs):
                continue

            if contains_test_files(root):
                all_test_dirs.add(root)

    return sorted(list(all_test_dirs))


def contains_test_files(directory):
    """Check if directory contains test files"""
    try:
        files = os.listdir(directory)
    except (PermissionError, OSError):
        return False

    test_patterns = ['test_*.py', '*_test.py', 'test*.py']
    for pattern in test_patterns:
        for file_name in files:
            if file_name.endswith('.py') and fnmatch.fnmatch(file_name, pattern):
                return True
    return 'conftest.py' in files


def parse_pytest_output_improved(output):
    """Parse pytest output to extract test cases with full paths"""
    tests = []

    for line in output.split('\n'):
        line = line.strip()
        if "::" not in line:
            continue
        tests.append(line)

    return tests
