import builtins
import ast
from agents.validation_agent import SecurityVisitor, ALLOWED_MODULES

class Sandbox:
    """
    Security execution wrapper. 
    Restricts available built-ins and uses unified AST validation to prevent 
    the AI from generating codes with unsafe operations (e.g., file system access, shell execution).
    """

    ALLOWED_MODULES = ALLOWED_MODULES
    
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
        Returns a restricted dictionary of Python built-ins.
        Explicitly removes functions like 'open', 'eval', 'exec', 'getattr', 'type'
        to prevent sandbox escape via introspection.
        """
        safe_names = [
            'abs', 'all', 'any', 'bool', 'dict', 'enumerate', 'filter',
            'float', 'format', 'hasattr', 'hash', 'hex', 'id', 'int',
            'isinstance', 'issubclass', 'iter', 'len', 'list', 'map', 'max',
            'min', 'next', 'oct', 'pow', 'print', 'range', 'repr', 'reversed',
            'round', 'set', 'slice', 'sorted', 'str', 'sum', 'tuple', 'zip',
            'Exception', 'ValueError', 'TypeError', 'KeyError', 'IndexError'
        ]
        safe_builtins = {name: getattr(builtins, name) for name in safe_names if hasattr(builtins, name)}
        safe_builtins['__import__'] = Sandbox.safe_import
        return safe_builtins
        
    @staticmethod
    def is_safe_code(code_string: str) -> bool:
        """
        Validates code against the unified AST SecurityVisitor.
        No brittle substring matching (avoids false positives on column/variable names).
        """
        try:
            tree = ast.parse(code_string)
            visitor = SecurityVisitor()
            visitor.visit(tree)
            return len(visitor.violations) == 0
        except SyntaxError:
            return False
