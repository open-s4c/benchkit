from benchkit.shell.commandAST.abstractTypes import Node, Visitor
from benchkit.shell.commandAST.nodes.commandNodes import CommandNode, StringNode
from benchkit.shell.commandAST.nodes.variable_node import Var


class printASTVisitor(Visitor):
    def __init__(self) -> None:
        self.indent = 0
    def printWithIndent(self,content:str):
        print("|"*self.indent + content)
    def printType(self,node:Node):
        self.printWithIndent(type(node).__name__)

    def __visitNodeCase(self,node:Node) -> Node:
        if isinstance(node,StringNode):
            self.printWithIndent(node.argument)
            node.visit(self)
            return node

        if isinstance(node,CommandNode):
            node.visit(self)
            return node

        if isinstance(node,Var):
            self.printWithIndent(node.name)
            node.visit(self)
            return node
        
        return node.visit(self)


    def visit_node(self,node:Node) -> Node:
        self.printType(node)
        self.indent += 1
        ret = self.__visitNodeCase(node)
        self.indent -= 1
        return ret