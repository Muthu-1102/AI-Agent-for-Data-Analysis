import builtins
import ast

class Sandbox:
    """
    Security execution wrapper. 
    Restricts available built-ins and performs basic static analysis to prevent 
    the AI from generating codes with unsafe operations (e.g., file system access, shell execution).
    """

    ALLOWED_MODULES = {
        'pandas', 'numpy', 'matplotlib', 'matplotlib.pyplot', 'seaborn', 'math', 'datetime'
    }
    
    @staticmethod
    def safe_import(name, globals=None, locals=None, fromlist=(), level=0):
        """
        Allows imports only from a small whitelist of safe scientific libraries.
        This is used when executing generated code inside the restricted sandbox.
        """
        base_name = name.split('.')[0]
        if name in Sandbox.ALLOWED_MODULES or base_name in Sandbox.ALLOWED_MODULES:
            return builtins.__import__(name, globals, locals, fromlist, level)
        raise ImportError(f"Import of module '{name}' is not permitted in the sandbox.")

    @staticmethod
    def get_safe_builtins() -> dict:
        """
        Returns a highly restricted dictionary of Python built-ins.
        Explicitly removes dangerous functions like 'open', 'eval', 'exec'.
        """
        safe_names = [
            'abs', 'all', 'any', 'bool', 'dict', 'dir', 'enumerate', 'filter',
            'float', 'format', 'getattr', 'hasattr', 'hash', 'hex', 'id', 'int',
            'isinstance', 'issubclass', 'iter', 'len', 'list', 'map', 'max',
            'min', 'next', 'oct', 'pow', 'print', 'range', 'repr', 'reversed',
            'round', 'set', 'slice', 'sorted', 'str', 'sum', 'tuple', 'type', 'zip',
            'Exception', 'ValueError', 'TypeError', 'KeyError', 'IndexError'
        ]
        safe_builtins = {name: getattr(builtins, name) for name in safe_names if hasattr(builtins, name)}
        safe_builtins['__import__'] = Sandbox.safe_import
        return safe_builtins
        
    @staticmethod
    def is_safe_code(code_string: str) -> bool:
        """
        Validates the AST (Abstract Syntax Tree) to ensure no dangerous modules
        are imported dynamically.
        """
        # Block literal keyword appearances for quick failure
        forbidden_keywords = ['__import__', 'eval', 'exec', 'open']
        for kw in forbidden_keywords:
            if kw in code_string:
                return False
                
        # AST-level validation to catch imports like `import os`, `import subprocess`
        try:
            tree = ast.parse(code_string)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
                    for alias in node.names:
                        # Allow only whitelisted safe analytical libraries
                        if alias.name not in ['pandas', 'numpy', 'matplotlib', 'matplotlib.pyplot', 'seaborn', 'math', 'datetime']:
                            return False
        except SyntaxError:
            # If the code can't be parsed, it's unsafe/invalid
            return False
            
        return True
