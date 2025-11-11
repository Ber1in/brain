      
#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import subprocess
import json
import sys
import re
import fnmatch
from collections import defaultdict

def setup_pythonpath():
    """设置PYTHONPATH，将脚本所在目录作为根目录"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 获取当前的PYTHONPATH
    current_path = os.environ.get('PYTHONPATH', '')
    
    # 添加脚本所在目录到PYTHONPATH的最前面
    new_path = "{}:{}".format(script_dir, current_path)
    
    # 设置环境变量
    os.environ['PYTHONPATH'] = new_path
    
    print("🔧 Setting PYTHONPATH:")
    print("   Root directory: {}".format(script_dir))
    print("   PYTHONPATH: {}".format(new_path))
    
    return script_dir

def collect_tests_with_detailed_report():
    """收集测试用例并生成详细报告，扫描父目录及其所有子目录"""
    
    # 首先设置PYTHONPATH
    root_dir = setup_pythonpath()
    
    # 指定要扫描的父目录
    parent_dirs = [
        "products/aidpu"
    ]
    
    exclude_dirs = [
        "products/beryl_chassis/1p1",
        "products/test/test_pytest_exit"
    ]
    
    # 确保父目录路径是相对于根目录的绝对路径
    parent_dirs = [os.path.join(root_dir, d) if not os.path.isabs(d) else d for d in parent_dirs]
    exclude_dirs = [os.path.join(root_dir, d) if not os.path.isabs(d) else d for d in exclude_dirs]
    
    all_tests = []
    test_details = []  # 存储详细的测试用例信息
    test_structure = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    scan_report = {
        "successful": [],
        "failed": [],
        "summary": {
            "total_dirs": 0,
            "successful_dirs": 0,
            "failed_dirs": 0,
            "total_tests": 0
        },
        "environment": {
            "root_directory": root_dir,
            "pythonpath": os.environ.get('PYTHONPATH', '')
        }
    }
    
    # 获取所有包含测试文件的目录（包括子目录）
    all_test_dirs = find_all_test_directories(parent_dirs, exclude_dirs, root_dir)
    
    # 用于跟踪已经扫描过的测试用例，避免重复
    scanned_tests = set()
    
    for test_dir in all_test_dirs:
        if not os.path.exists(test_dir):
            print("❌ Directory not found: {}".format(test_dir))
            scan_report["failed"].append({
                "directory": test_dir,
                "reason": "Directory does not exist"
            })
            continue
            
        scan_report["summary"]["total_dirs"] += 1
        
        # 获取相对于根目录的路径用于显示
        relative_dir = os.path.relpath(test_dir, root_dir) if test_dir.startswith(root_dir) else test_dir
        print("\n🔍 Scanning directory: {}".format(relative_dir))
        
        # 构建pytest命令，确保使用正确的环境
        cmd = ["pytest", "--collect-only", "-q", test_dir]
        
        try:
            # 使用当前进程的环境变量（包含设置好的PYTHONPATH）
            result = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=os.environ)
            stdout, stderr = result.communicate()
            stderr_output = stderr.decode('utf-8')
            
            if result.returncode == 0:
                # 成功收集
                output = stdout.decode('utf-8')
                tests, structure, details = parse_pytest_output_with_duplicate_check(output, test_dir, root_dir, scanned_tests)
                
                # 只添加新的测试用例
                new_tests = [t for t in tests if t not in scanned_tests]
                all_tests.extend(new_tests)
                test_details.extend(details)
                
                # 更新已扫描的测试用例集合
                scanned_tests.update(tests)
                
                # 更新结构：目录 -> 文件 -> 类 -> 测试用例
                for file_path, classes in structure.items():
                    # 将文件路径转换为相对于根目录的路径
                    rel_file_path = os.path.relpath(file_path, root_dir) if file_path.startswith(root_dir) else file_path
                    for class_name, test_cases in classes.items():
                        # 只添加新的测试用例
                        existing_cases = test_structure[relative_dir][rel_file_path][class_name]
                        new_cases = [tc for tc in test_cases if tc not in existing_cases]
                        test_structure[relative_dir][rel_file_path][class_name].extend(new_cases)
                    
                print("✅ Found {} test cases ({} new)".format(len(tests), len(new_tests)))
                scan_report["successful"].append({
                    "directory": relative_dir,
                    "absolute_directory": test_dir,
                    "test_count": len(tests),
                    "new_test_count": len(new_tests),
                    "files": list(structure.keys())
                })
                scan_report["summary"]["successful_dirs"] += 1
                scan_report["summary"]["total_tests"] += len(new_tests)
                
            else:
                # 收集失败，分析原因
                error_reason = analyze_failure_reason(stderr_output, test_dir)
                print("❌ Failed to scan: {}".format(error_reason))
                
                scan_report["failed"].append({
                    "directory": relative_dir,
                    "absolute_directory": test_dir,
                    "reason": error_reason,
                    "error_output": stderr_output[:500]  # 只保存前500字符
                })
                scan_report["summary"]["failed_dirs"] += 1
                        
        except Exception as e:
            error_msg = "Unexpected error: {}".format(str(e))
            print("❌ Error: {}".format(error_msg))
            scan_report["failed"].append({
                "directory": relative_dir,
                "absolute_directory": test_dir,
                "reason": error_msg
            })
            scan_report["summary"]["failed_dirs"] += 1
    
    return all_tests, test_structure, scan_report, test_details

def find_all_test_directories(parent_dirs, exclude_dirs, root_dir):
    """查找所有包含测试文件的目录（包括子目录）"""
    all_test_dirs = set()
    
    for parent_dir in parent_dirs:
        if not os.path.exists(parent_dir):
            print("⚠️ Warning: Parent directory not found: {}".format(parent_dir))
            continue
            
        print("🔎 Searching for test directories in: {}".format(
            os.path.relpath(parent_dir, root_dir) if parent_dir.startswith(root_dir) else parent_dir
        ))
        
        # 递归查找所有包含测试文件的目录
        for root, dirs, files in os.walk(parent_dir):
            # 移除排除的目录
            dirs[:] = [d for d in dirs if not should_exclude_directory(os.path.join(root, d), exclude_dirs)]
            
            # 检查当前目录是否应该被排除
            if should_exclude_directory(root, exclude_dirs):
                continue
                
            # 检查当前目录是否包含测试文件
            if contains_test_files(root):
                all_test_dirs.add(root)
                print("   📁 Found test directory: {}".format(
                    os.path.relpath(root, root_dir) if root.startswith(root_dir) else root
                ))
    
    # 转换为列表并排序
    all_test_dirs = sorted(list(all_test_dirs))
    print("\n📁 Found {} test directories to scan:".format(len(all_test_dirs)))
    for dir_path in all_test_dirs:
        relative_path = os.path.relpath(dir_path, root_dir) if dir_path.startswith(root_dir) else dir_path
        print("  - {}".format(relative_path))
    
    return all_test_dirs

def should_exclude_directory(directory, exclude_dirs):
    """检查目录是否应该被排除"""
    for exclude_dir in exclude_dirs:
        if directory.startswith(exclude_dir):
            return True
    return False

def contains_test_files(directory):
    """检查目录是否包含测试文件"""
    try:
        files = os.listdir(directory)
    except (PermissionError, OSError):
        return False
    
    test_patterns = [
        'test_*.py',
        '*_test.py',
        'test*.py'
    ]
    
    for pattern in test_patterns:
        for file_name in files:
            if (file_name.endswith('.py') and 
                fnmatch.fnmatch(file_name, pattern)):
                return True
    
    # 检查是否有conftest.py
    if 'conftest.py' in files:
        return True
        
    return False

def parse_pytest_output_with_duplicate_check(output, base_dir, root_dir, existing_tests):
    """解析pytest输出，并检查重复的测试用例"""
    tests = []
    test_details = []  # 存储详细的测试用例信息
    structure = defaultdict(lambda: defaultdict(list))  # 文件 -> 类 -> 测试用例列表
    current_file = ""
    current_class = ""
    
    for line in output.split('\n'):
        line = line.strip()
        if not line or 'no tests ran' in line or '===' in line:
            continue
            
        # 匹配模块
        if line.startswith('<Module '):
            file_name = line.split(' ')[1].replace('.py>', '.py')
            # 转换为绝对路径
            current_file = os.path.join(base_dir, file_name) if not os.path.isabs(file_name) else file_name
            current_class = ""  # 重置当前类
        # 匹配类
        elif line.startswith('<Class '):
            class_name = line.split(' ')[1].replace('>', '')
            current_class = class_name
        # 匹配函数（测试用例）
        elif line.startswith('<Function '):
            test_name = line.split(' ')[1].replace('>', '')
            
            # 构建完整的测试路径（使用相对路径）
            rel_file_path = os.path.relpath(current_file, root_dir) if current_file.startswith(root_dir) else current_file
            if current_class:
                full_test_path = "{}::{}::{}".format(rel_file_path, current_class, test_name)
            else:
                full_test_path = "{}::{}".format(rel_file_path, test_name)
            
            # 检查是否已经存在这个测试用例
            if full_test_path not in existing_tests:
                tests.append(full_test_path)
                
                # 存储详细的测试用例信息
                test_details.append({
                    "test_path": full_test_path,
                    "file_path": rel_file_path,
                    "absolute_file_path": current_file,
                    "class_name": current_class if current_class else None,
                    "test_name": test_name,
                    "directory": base_dir
                })
                
                # 更新结构
                if current_class:
                    structure[current_file][current_class].append(test_name)
                else:
                    # 如果没有类，放在一个特殊的键下
                    structure[current_file]["NoClass"].append(test_name)
    
    return tests, structure, test_details

def analyze_failure_reason(stderr_output, test_dir):
    """分析收集失败的原因"""
    if not stderr_output:
        return "No error output available"
    
    stderr_lower = stderr_output.lower()
    
    # 检查模块导入错误
    if "module" in stderr_lower and "not found" in stderr_lower:
        module_match = re.search(r"ModuleNotFoundError: No module named '([^']+)'", stderr_output)
        if module_match:
            missing_module = module_match.group(1)
            return "Missing module: {}".format(missing_module)
    
    # 检查文件缺失错误
    if "no such file or directory" in stderr_lower:
        file_match = re.search(r"No such file or directory: '([^']+)'", stderr_output)
        if file_match:
            missing_file = file_match.group(1)
            return "Missing required file: {}".format(missing_file)
        return "Missing required configuration file"
    
    # 检查配置冲突
    if "conftest" in stderr_lower and "already added" in stderr_lower:
        option_match = re.search(r"option names \{'([^']+)'\} already added", stderr_output)
        if option_match:
            option_name = option_match.group(1)
            return "Configuration conflict: option '{}' already exists".format(option_name)
        return "Configuration conflict in conftest.py"
    
    # 检查语法错误
    if "syntaxerror" in stderr_lower:
        syntax_match = re.search(r"SyntaxError: ([^\n]+)", stderr_output)
        if syntax_match:
            return "Syntax error: {}".format(syntax_match.group(1))
        return "Syntax error in Python files"
    
    # 检查导入错误
    if "importerror" in stderr_lower:
        import_match = re.search(r"ImportError: ([^\n]+)", stderr_output)
        if import_match:
            return "Import error: {}".format(import_match.group(1))
        return "Import error (missing dependencies)"
    
    # 检查值错误
    if "valueerror" in stderr_lower:
        value_match = re.search(r"ValueError: ([^\n]+)", stderr_output)
        if value_match:
            return "Configuration error: {}".format(value_match.group(1))
        return "Configuration error"
    
    # 检查收集错误
    if "error collecting" in stderr_lower:
        error_match = re.search(r"ERROR collecting.*?([^\n]+)", stderr_output)
        if error_match:
            return "Collection error: {}".format(error_match.group(1))
        return "Test collection error"
    
    # 提取第一行有意义的错误信息
    lines = stderr_output.split('\n')
    for line in lines:
        line = line.strip()
        if line and not line.startswith('=') and len(line) > 10:
            return line[:200]
    
    return "Unknown error (check detailed error output)"

def build_tree_structure(test_structure, root_dir):
    """构建树状结构"""
    tree = {"name": "All Tests", "type": "root", "children": []}
    
    for directory, files in test_structure.items():
        # 使用相对路径显示
        rel_dir = os.path.relpath(directory, root_dir) if directory.startswith(root_dir) else directory
        dir_node = {
            "name": rel_dir,
            "type": "directory", 
            "absolute_path": directory,
            "children": []
        }
        
        for file_path, classes in files.items():
            rel_file_path = os.path.relpath(file_path, root_dir) if file_path.startswith(root_dir) else file_path
            file_node = {
                "name": os.path.basename(file_path),
                "type": "file",
                "path": rel_file_path,
                "absolute_path": file_path,
                "children": []
            }
            
            for class_name, test_cases in classes.items():
                class_node = {
                    "name": class_name if class_name != "NoClass" else "Functions",
                    "type": "class",
                    "children": []
                }
                
                for test_case in test_cases:
                    # 构建完整的pytest路径
                    if class_name != "NoClass":
                        full_path = "{}::{}::{}".format(rel_file_path, class_name, test_case)
                    else:
                        full_path = "{}::{}".format(rel_file_path, test_case)
                    
                    test_node = {
                        "name": test_case,
                        "type": "test_case",
                        "full_path": full_path
                    }
                    class_node["children"].append(test_node)
                
                file_node["children"].append(class_node)
            
            dir_node["children"].append(file_node)
        
        tree["children"].append(dir_node)
    
    return tree

def generate_pytest_commands(test_structure, root_dir):
    """生成pytest执行命令，用于单个测试用例执行"""
    pytest_commands = {}
    
    for directory, files in test_structure.items():
        for file_path, classes in files.items():
            # 使用相对路径
            rel_file_path = os.path.relpath(file_path, root_dir) if file_path.startswith(root_dir) else file_path
            for class_name, test_cases in classes.items():
                for test_case in test_cases:
                    # 构建完整的pytest路径（相对路径）
                    if class_name != "NoClass":
                        full_test_path = "{}::{}::{}".format(rel_file_path, class_name, test_case)
                    else:
                        full_test_path = "{}::{}".format(rel_file_path, test_case)
                    
                    # 生成pytest命令
                    pytest_command = "pytest {} -v".format(full_test_path)
                    pytest_commands[full_test_path] = {
                        "command": pytest_command,
                        "absolute_path": "{}::{}::{}".format(file_path, class_name, test_case) if class_name != "NoClass" else "{}::{}".format(file_path, test_case),
                        "file_path": rel_file_path,
                        "absolute_file_path": file_path
                    }
    
    return pytest_commands

def export_comprehensive_report(all_tests, test_structure, scan_report, root_dir, test_details):
    """导出综合报告"""
    
    # 1. 测试用例列表（包含文件路径信息）
    with open("all_test_cases.txt", "w") as f:
        f.write("Total test cases: {}\n".format(len(all_tests)))
        f.write("Root directory: {}\n".format(root_dir))
        f.write("PYTHONPATH: {}\n\n".format(os.environ.get('PYTHONPATH', '')))
        
        if test_details:
            for i, test_detail in enumerate(test_details, 1):
                f.write("{:4d}. {}\n".format(i, test_detail["test_path"]))
                f.write("     File: {}\n".format(test_detail["file_path"]))
                if test_detail["class_name"]:
                    f.write("     Class: {}\n".format(test_detail["class_name"]))
                f.write("     Test: {}\n".format(test_detail["test_name"]))
                f.write("     Absolute File: {}\n\n".format(test_detail["absolute_file_path"]))
        else:
            f.write("No test cases found.\n")
    
    # 2. 简化的测试用例列表（仅路径）
    with open("test_cases_simple.txt", "w") as f:
        f.write("Total test cases: {}\n\n".format(len(all_tests)))
        for i, test in enumerate(all_tests, 1):
            f.write("{:4d}. {}\n".format(i, test))
    
    # 3. 树状结构
    with open("test_structure_tree.txt", "w") as f:
        f.write("Test Case Structure Tree\n")
        f.write("Root directory: {}\n".format(root_dir))
        f.write("=" * 50 + "\n\n")
        
        def write_tree(node, indent=0, file_obj=f):
            prefix = "  " * indent
            if node["type"] == "root":
                file_obj.write("All Tests\n")
            elif node["type"] == "directory":
                file_obj.write("{}+-- {} ({})\n".format(prefix, node["name"], node["absolute_path"]))
            elif node["type"] == "file":
                file_obj.write("{}+-- {} ({} classes)\n".format(prefix, node["name"], len(node["children"])))
            elif node["type"] == "class":
                file_obj.write("{}+-- {} ({} tests)\n".format(prefix, node["name"], len(node["children"])))
            elif node["type"] == "test_case":
                file_obj.write("{}+-- {}\n".format(prefix, node["name"]))
            
            if "children" in node:
                for child in node["children"]:
                    write_tree(child, indent + 1, file_obj)
        
        tree = build_tree_structure(test_structure, root_dir)
        write_tree(tree)
    
    # 4. 扫描报告
    with open("scan_report.md", "w") as f:
        f.write("# Test Case Collection Report\n\n")
        f.write("## Environment\n")
        f.write("- Root directory: `{}`\n".format(root_dir))
        f.write("- PYTHONPATH: `{}`\n\n".format(os.environ.get('PYTHONPATH', '')))
        
        f.write("## Summary\n")
        f.write("- Total directories scanned: {}\n".format(scan_report["summary"]["total_dirs"]))
        f.write("- Successful directories: {}\n".format(scan_report["summary"]["successful_dirs"]))
        f.write("- Failed directories: {}\n".format(scan_report["summary"]["failed_dirs"]))
        f.write("- Total test cases collected: {}\n\n".format(scan_report["summary"]["total_tests"]))
        
        f.write("## Successful Directories\n")
        for success in scan_report["successful"]:
            f.write("- **{}**: {} test cases\n".format(success["directory"], success["test_count"]))
        
        f.write("\n## Failed Directories\n")
        for failure in scan_report["failed"]:
            f.write("### {}\n".format(failure["directory"]))
            f.write("**Absolute path**: {}\n\n".format(failure["absolute_directory"]))
            f.write("**Reason**: {}\n\n".format(failure["reason"]))
            if "error_output" in failure:
                f.write("```\n{}\n```\n\n".format(failure["error_output"]))
    
    # 5. pytest命令文件
    pytest_commands = generate_pytest_commands(test_structure, root_dir)
    with open("pytest_commands.txt", "w") as f:
        f.write("# Pytest commands for individual test execution\n")
        f.write("# Root directory: {}\n".format(root_dir))
        f.write("# PYTHONPATH: {}\n".format(os.environ.get('PYTHONPATH', '')))
        f.write("# Total commands: {}\n\n".format(len(pytest_commands)))
        for i, (test_path, command_info) in enumerate(pytest_commands.items(), 1):
            f.write("# {}. {}\n".format(i, test_path))
            f.write("# File: {}\n".format(command_info["file_path"]))
            f.write("# Absolute path: {}\n".format(command_info["absolute_path"]))
            f.write("{}\n\n".format(command_info["command"]))
    
    # 6. 环境设置脚本
    with open("setup_environment.sh", "w") as f:
        f.write("#!/bin/bash\n")
        f.write("# Environment setup script for test execution\n")
        f.write("export PYTHONPATH={}:$PYTHONPATH\n".format(root_dir))
        f.write('echo "PYTHONPATH set to: $PYTHONPATH"\n')
    
    # 7. JSON格式（包含详细的测试用例信息）
    with open("test_data.json", "w") as f:
        data = {
            "environment": {
                "root_directory": root_dir,
                "pythonpath": os.environ.get('PYTHONPATH', '')
            },
            "test_cases": all_tests,
            "test_cases_detailed": test_details,
            "structure": test_structure,
            "pytest_commands": pytest_commands,
            "report": scan_report
        }
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print("\n📊 Export completed!")
    print("📁 Generated files:")
    print("  - all_test_cases.txt    : 详细测试用例列表（包含文件路径）")
    print("  - test_cases_simple.txt : 简化测试用例列表")
    print("  - test_structure_tree.txt : 树状结构")
    print("  - pytest_commands.txt   : Pytest执行命令")
    print("  - scan_report.md        : 详细扫描报告")
    print("  - setup_environment.sh  : 环境设置脚本")
    print("  - test_data.json        : 所有数据的JSON格式")

if __name__ == "__main__":
    print("🚀 Starting comprehensive test case collection (all subdirectories)...")
    
    all_tests, test_structure, scan_report, test_details = collect_tests_with_detailed_report()
    
    root_dir = scan_report["environment"]["root_directory"]
    
    print("\n" + "="*70)
    print("📈 COLLECTION SUMMARY")
    print("="*70)
    print("Root directory: {}".format(root_dir))
    print("PYTHONPATH: {}".format(os.environ.get('PYTHONPATH', '')))
    print("Total directories: {}".format(scan_report["summary"]["total_dirs"]))
    print("✅ Successful: {}".format(scan_report["summary"]["successful_dirs"]))
    print("❌ Failed: {}".format(scan_report["summary"]["failed_dirs"]))
    print("📋 Total test cases: {}".format(scan_report["summary"]["total_tests"]))
    
    if scan_report["failed"]:
        print("\n🔍 Failed directories analysis:")
        for failure in scan_report["failed"]:
            print("  - {}: {}".format(failure["directory"], failure["reason"]))
    
    export_comprehensive_report(all_tests, test_structure, scan_report, root_dir, test_details)

    