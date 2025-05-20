from typing import List

from benchkit.shell.commandAST.abstractTypes import *

class StringNode(Node):
    def __init__(self,argument:str) -> None:
        self.argument=argument
    def visit(self,visitor:Visitor):
        return self


class CommandNode(Node):
    def __init__(self,command:Node,arguments:None|List[Node]=None) -> None:
        self.command:Node =command
        if arguments is None:
            arguments = []
        self.arguments:List[Node]=arguments
    
    def visit(self,visitor:Visitor):
        self.command = visitor.visit_node(self.command)
        self.arguments = list(map(visitor.visit_node, self.arguments))
        return self
    
class InlineCommandNode(CommandNode):
    def __init__(self, command:CommandNode, arguments:List[Node] | None = None):
        super().__init__(command, arguments)
    def visit(self, visitor:Visitor):
        super().visit(visitor)
        return self
    
         