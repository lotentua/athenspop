#  Copyright (c) 2022 Theodore Chatziioannou
#  Copyright (c) 2025 Laboratory of Transportation Engineering, SRSGE, NTUA
#  This software is licensed under the MIT License.

import ast
import os


class UsageAnalyzer(ast.NodeVisitor):
    def __init__(self):
        self.current_function = None
        self.args = {}
        self.usage_counts = {}
        self.issues = []

    def visit_FunctionDef(self, node):
        self.current_function = node.name
        # Get list of argument names
        self.args = {arg.arg for arg in node.args.args}
        if "self" in self.args:
            self.args.remove("self")  # Ignore 'self' in methods
        if "cls" in self.args:
            self.args.remove("cls")  # Ignore 'cls'

        self.usage_counts = dict.fromkeys(self.args, 0)

        # Visit all nodes in the function body
        for item in node.body:
            self.visit(item)

        # Check for under-utilized objects
        for arg, count in self.usage_counts.items():
            # Threshold: If accessed 2 or fewer times
            if 0 < count <= 2:
                self.issues.append(
                    f"Function '{node.name}': Argument '{arg}' is used only {count} time(s)."
                )

        # Reset for next function
        self.current_function = None

    def visit_Attribute(self, node):
        # Check if we are accessing an attribute of one of the arguments
        # e.g. config.db_url -> node.value.id == 'config'
        if isinstance(node.value, ast.Name) and node.value.id in self.args:
            self.usage_counts[node.value.id] += 1
        self.generic_visit(node)


def analyze_file(filename):
    with open(filename, encoding="utf-8") as f:
        try:
            tree = ast.parse(f.read())
            analyzer = UsageAnalyzer()
            analyzer.visit(tree)
            for issue in analyzer.issues:
                print(f"{filename} -> {issue}")
        except Exception:
            pass  # Skip files that fail to parse


# Run the analysis
for root, dirs, files in os.walk("."):
    for file in files:
        if file.endswith(".py"):
            analyze_file(os.path.join(root, file))
