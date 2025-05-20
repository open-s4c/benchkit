#!/usr/bin/env python3

from benchkit.shell.commandAST.command import command
from benchkit.shell.commandAST.nodes.variable_node import RuntimeVariable
from benchkit.shell.commandAST.visitor import printAst


def localtests():

    commandres = command("'ls -R'",["arg0","arg1"])
    print("-------------------------------------------")
    printAst(commandres)
    commandres = command("'ls -R '",["arg0","arg1"])
    print("-------------------------------------------")
    printAst(commandres)
    commandres = command("' ls -R'",["arg0","arg1"])
    print("-------------------------------------------")
    printAst(commandres)
    commandres = command("ls -R",["arg0","arg1"])
    print("-------------------------------------------")
    printAst(commandres)
    commandres = command("ls -R   ",["arg0","arg1"])
    print("-------------------------------------------")
    printAst(commandres)
    commandres = command("   ls -R",["arg0","arg1"])
    print("-------------------------------------------")
    printAst(commandres)
    commandres = command("ls     -R",["arg0","arg1"])
    print("-------------------------------------------")
    printAst(commandres)
    commandres = command("ls",["arg0","arg1"])
    print("-------------------------------------------")
    printAst(commandres)
    print("-------------------------------------------")
    commandres = command("ls     -R",[RuntimeVariable("QQ",[1,2]),"arg1"])
    printAst(commandres)

if __name__ == "__main__":
    
    

    localtests()