import ast
from typing import Dict, Any

from core.pipeline import PipelineStep, step_logging_wrapper

# Define an explicit whitelist of safe modules for Data Analysis.
# Any import outside this list will trigger a security violation.
ALLOWED_MODULES = {
    "pandas", "numpy", "matplotlib", "matplotlib.pyplot", "seaborn", 
    "math", "datetime", "scipy", "statsmodels", "re", "collections",
    "itertools", "json"
}

class SecurityVisitor(ast.NodeVisitor):
    def __init__(self):
        self.violations = []

    def visit_Import(self, node):
        for alias in node.names:
            base_module = alias.name.split('.')[0]
            if base_module not in ALLOWED_MODULES and alias.name not in ALLOWED_MODULES:
                self.violations.append(f"Unsafe import blocked: '{alias.name}'")
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module:
            base_module = node.module.split('.')[0]
            if base_module not in ALLOWED_MODULES and node.module not in ALLOWED_MODULES:
                self.violations.append(f"Unsafe from-import blocked: '{node.module}'")
        self.generic_visit(node)
        
    # Additionally explicitly block highly dangerous built-ins to seal up the sandbox
    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            if node.func.id in {'eval', 'exec', 'open', 'compile', 'input', '__import__'}:
                self.violations.append(f"Unsafe built-in function blocked: '{node.func.id}'")
        self.generic_visit(node)

class ValidationAgent(PipelineStep):
    """
    Security Engineer Agent responsible for validating generated Python code.
    It uses Python's precise AST parsing to detect and block unsafe imports,
    system calls, or malicious built-ins before the code is executed.
    """
    
    @step_logging_wrapper
    async def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        generated_code = state.get("generated_code")
        
        if not generated_code:
            raise ValueError("ValidationAgent requires 'generated_code' in the state context.")
            
        # 1. Check for Syntax Errors first
        try:
            tree = ast.parse(generated_code)
        except SyntaxError as e:
            # If the code isn't valid Python, we reject it immediately
            raise ValueError(f"Syntax Error in generated code: {str(e)}")
            
        # 2. Walk the AST to check for security policy violations
        visitor = SecurityVisitor()
        visitor.visit(tree)
        
        if visitor.violations:
            violation_msg = "; ".join(visitor.violations)
            # Security violations immediately halt the pipeline tightly.
            raise PermissionError(f"Code validation failed due to security violations: {violation_msg}")
            
        # 3. Validation passed
        return {
            "validation_passed": True,
            "validation_message": "Success! Code passed strict AST security checks."
        }
