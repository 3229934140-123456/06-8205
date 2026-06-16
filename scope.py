from dataclasses import dataclass, field
from typing import Any, Optional, List
from calc_ast import FunctionDefNode


@dataclass
class FunctionValue:
    name: str
    params: List[str]
    body: FunctionDefNode
    closure: 'Scope'

    def __repr__(self) -> str:
        return f"FunctionValue({self.name}({', '.join(self.params)}))"


class Scope:
    def __init__(self, parent: Optional['Scope'] = None, name: str = "global"):
        self.parent = parent
        self.name = name
        self.variables: dict[str, Any] = {}
        self.functions: dict[str, FunctionValue] = {}
        self.children: List['Scope'] = []
        if parent:
            parent.children.append(self)

    def define_variable(self, name: str, value: Any) -> None:
        self.variables[name] = value

    def define_function(self, name: str, func: FunctionValue) -> None:
        self.functions[name] = func

    def lookup_variable(self, name: str) -> Any:
        if name in self.variables:
            return self.variables[name]
        if self.parent:
            return self.parent.lookup_variable(name)
        raise NameError(f"Undefined variable '{name}'")

    def lookup_function(self, name: str) -> FunctionValue:
        if name in self.functions:
            return self.functions[name]
        if self.parent:
            return self.parent.lookup_function(name)
        raise NameError(f"Undefined function '{name}'")

    def has_variable_local(self, name: str) -> bool:
        return name in self.variables

    def has_function_local(self, name: str) -> bool:
        return name in self.functions

    def assign_variable(self, name: str, value: Any) -> None:
        scope = self._find_variable_scope(name)
        if scope:
            scope.variables[name] = value
        else:
            self.variables[name] = value

    def _find_variable_scope(self, name: str) -> Optional['Scope']:
        if name in self.variables:
            return self
        if self.parent:
            return self.parent._find_variable_scope(name)
        return None

    def create_child_scope(self, name: str = "local") -> 'Scope':
        return Scope(parent=self, name=name)

    def __repr__(self) -> str:
        vars_str = ", ".join(f"{k}={v}" for k, v in self.variables.items())
        funcs_str = ", ".join(self.functions.keys())
        return f"Scope({self.name}, vars=[{vars_str}], funcs=[{funcs_str}])"
