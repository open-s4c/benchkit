#!/usr/bin/env python3

import shlex
import subprocess
from typing import Dict
from benchkit.shell.commandAST.Visitors.print_visitor import printASTVisitor
from benchkit.shell.commandAST.Visitors.variable_visitors import VariableFinder, resolveAllVariables
from benchkit.shell.commandAST.Visitors.verification_visitors import OnlyStringAndCommandNodesChecker
from benchkit.shell.commandAST.abstractTypes import *
from benchkit.shell.commandAST.abstractTypes import Node
from benchkit.shell.commandAST.nodes.commandNodes import *
from benchkit.shell.commandAST.nodes.variable_node import *
from benchkit.shell.commandAST.command import command
    
def VariableDuplicateDetector(ast:Node):
    variable_finder = VariableFinder()
    variable_finder.visitAST(ast)
    var_names = list(map(lambda x: x.name,variable_finder.variables))
    for var_name in var_names:
        if var_names.count(var_name) >=2:
            raise NameError(f"The variable name {var_name} occures in two sepperate objects")

def CheckReadyForConversionToCommand(ast:CommandNode):
    #TODO: I want to make a grammar checker this will do for now
    check = OnlyStringAndCommandNodesChecker()
    ast.visit(check)
    

def convertComandToString(ast:CommandNode) -> str:
    class CommandToStringVisitor(Visitor):
        def visit_node(self, node: Node) -> Node:
            if isinstance(node,CommandNode):
                new_arg_list = []
                for arg in node.arguments:
                    if isinstance(arg,InlineCommandNode):
                        converted_ast = arg.visit(converter)
                        new_arg_list.append(converted_ast.command)
                        new_arg_list += converted_ast.arguments
                    else:
                        new_arg_list.append(arg)
                    node.arguments = new_arg_list
                return StringNode(convertComandToString(node))
            return node.visit(self)

    converter = CommandToStringVisitor()
    converted_ast = ast.visit(converter)

    args = [x.argument for x in converted_ast.arguments]
    args.insert(0,converted_ast.command.argument)
    print(args)
    return shlex.join(args)

# Functions to hide away visitors
def printAst(ast:Node):
    v = printASTVisitor()
    v.visitAST(ast)

def resolveAllVariablesWithDict(ast:Node,d:Dict[str,str]):
    variable_resolver = resolveAllVariables(d)
    # check if amountOfTimeToSleep is not used twice in the command by dfferent vars resulting in wrong assignment possibly
    VariableDuplicateDetector(ast)
    
    # Resolve the vars given an assignment dictionairy
    return variable_resolver.visitAST(ast)

def getString(ast:Node):

    # Make sure that the command has been sufficiently resolved by visitors, aka there are no leftovers from bad patterns
    CheckReadyForConversionToCommand(ast)

    # Convert the ast to a string and print it
    return convertComandToString(ast)

def execute_on_remote(ast:Node,host:str,port:int) -> Node:
    return command("ssh", [host, "-p",str(port), "-t", ast])

def inline(ast:CommandNode) -> InlineCommandNode:
    return InlineCommandNode(ast.command,ast.arguments)


"""
Tests for the file to show that the functions are working
"""
def localtests():
    amount_of_time_to_sleep = RuntimeVariable("amountOfTimeToSleep",[1,2,5,40])
    main_command_ast = command("sleep",[amount_of_time_to_sleep])
    full_command = command("perf stat",[inline(main_command_ast), "-a"])
    remote_command = execute_on_remote(full_command,"user@host",port=57429)
    printAst(remote_command)

    resolved_command = resolveAllVariablesWithDict(
        remote_command,{
            "amountOfTimeToSleep":"40",
        })

    string = getString(resolved_command)

    print(string)

def newtest():
    c = command("ssh user@host -p 57429 -t 'perf stat sleep 1'")
    printAst(c)
    string = getString(c)
    print(string)

def runtest():
    t = shlex.split("perf stat 'sleep 10' -a")
    print(t)

    main_command_ast = command("sleep",["1"])
    full_command = command("perf stat",[inline(main_command_ast)])
    remote_command = execute_on_remote(full_command,"user@host",port=57429)
    printAst(remote_command)
    string = getString(remote_command)
    print(string)
    local_proc_1 = subprocess.Popen(string, shell=True,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
    outs, errs = local_proc_1.communicate()
    retcode = local_proc_1.poll()
    output = outs
    print(retcode)
    print(str(output.decode("utf-8")))


if __name__ == "__main__":
    localtests()
    newtest()
    runtest()
