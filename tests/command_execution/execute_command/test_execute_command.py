import itertools
import os
import pathlib
from typing import Any, Dict, List, Optional, Tuple
import unittest

from benchkit.shell.CommunicationLayer.IO_stream import ReadableIOStream, WritableIOStream
from benchkit.shell.CommunicationLayer.OutputObject import Output
from benchkit.shell.CommunicationLayer.hooks.basic_hooks import create_stream_line_logger_hook, create_voiding_result_hook, logger_line_hook, std_out_result_void_err, void_hook
from benchkit.shell.CommunicationLayer.hooks.hook import IOHook, IOResultHook, IOWriterHook, OutputHook
from benchkit.shell.ast_shell_out import execute_command

def get_arguments_dict_list(
    overwrite_arguments_dict: Dict[str, Any] | None = None,
):
    if overwrite_arguments_dict is None:
        overwrite_arguments_dict = {}

    arguments_dict:Dict[str,Any] = {}

    for argument_key in overwrite_arguments_dict:
        arguments_dict[argument_key] = overwrite_arguments_dict[argument_key]

    keys:List[str] = []
    arguments:List[Any] = []

    for key, arugments in arguments_dict.items():
        keys.append(key)
        arguments += [arugments]
    argument_permutations = itertools.product(*arguments)
    result_list:List[Dict[str,Any]] = []
    for argument_permutation in list(argument_permutations):
        result_list.append(dict(zip(keys, argument_permutation)))
    return result_list

def generate_test_hook_lists(force_output:bool=False,dont_void_output:bool=False) -> List[Tuple[List[IOHook],List[OutputHook],Optional[IOResultHook]]]:

    def useless_func(input_object: ReadableIOStream, output_object: WritableIOStream):
        outline = input_object.read(10)
        while outline:
            output_object.write(outline)
            outline = input_object.read(10)

    def gen_useless_input():
        return IOWriterHook(useless_func)

    def gen_logging_input():
        return create_stream_line_logger_hook("log_input" + " {}")

    def gen_useless_output():
        return OutputHook(IOWriterHook(useless_func),IOWriterHook(useless_func))

    def gen_logging_output():
        return logger_line_hook(
            "\033[34m[OUT | ]\033[0m" + " {}",
            "\033[91m[ERR | ]\033[0m" + " {}",
        )

    def gen_result_output():
        output_hook_object = create_voiding_result_hook()
        voiding_result_hook = OutputHook(output_hook_object,None)
        return voiding_result_hook, output_hook_object

    hooklist:List[Tuple[List[IOHook],List[OutputHook],Optional[IOResultHook]]] = []

    for option in itertools.product([True,False],[True,False],[True,False],[True,False],[True,False]):
        output_hooks:List[OutputHook] = []
        input_hooks:List[IOHook] = []
        output_object = None
        if option[0]:
            input_hooks.append(gen_useless_input())
        if option[1]:
            input_hooks.append(gen_logging_input())
        if option[2]:
            output_hooks.append(gen_useless_output())
        if option[3]:
            output_hooks.append(gen_logging_output())
        if option[4] or force_output:
            hook, obj = gen_result_output()
            output_object = obj
            output_hooks.append(hook)
        if not dont_void_output:
            output_hooks.append(void_hook())

        hooklist.append((input_hooks, output_hooks, output_object))
    return hooklist


class BasicShellTests(unittest.TestCase):

    @unittest.skip("disabled for debugging")
    def test_echo(self) -> None:
        """Basic tests to see if the command-line executes the command and can return output"""

        # standard arguments
        arguments_list = get_arguments_dict_list(
            {
                'current_dir':[None, pathlib.Path(__file__).parent.resolve(),pathlib.Path('/')],
                'environment':[None,{'test':'test'},{'a':'12','b':'11'},{}],
                'timeout':[None,1,10,99999999999],
                'ignore_ret_codes':[None,(1,),(1,7,),()],
            }
        )
        for arguments in arguments_list:

            # hook based argumens
            hooklist = generate_test_hook_lists(force_output=True)
            for input_hooks,output_hooks,result_hook_object in hooklist:

                # execution
                execute_command(
                        ["echo", "benchkit_echo_test", str(arguments)],
                        ordered_output_hooks=output_hooks,
                        ordered_input_hooks=input_hooks,
                        **arguments,
                    )

                # result gathering
                output = result_hook_object.get_result()
                expected_output = f"benchkit_echo_test {str(arguments)}\n".encode("utf-8")
                self.assertEqual(
                        output,
                        expected_output,
                        "shell does not provide the right output in the result",
                    )

    @unittest.skip("disabled for debugging")
    def test_environment(self) -> None:
        """Test to see if the env of the command is correcly set to the given env"""

        # standard arguments
        arguments_list = get_arguments_dict_list(
            {
                'current_dir':[None, pathlib.Path(__file__).parent.resolve(),pathlib.Path('/')],
                'environment':[None,{'test':'test'},{'a':'12','b':'11'},{}],
                'timeout':[None,1,10,99999999999],
                'ignore_ret_codes':[None,(1,),(1,7,),()],
            }
        )
        for arguments in arguments_list:

            # hook based argumens
            hooklist = generate_test_hook_lists(force_output=True)
            for input_hooks,output_hooks,result_hook_object in hooklist:

                # execution
                execute_command(
                        ["env"],
                        ordered_output_hooks=output_hooks,
                        ordered_input_hooks=input_hooks,
                        **arguments,
                    )
                env = result_hook_object.get_result()
                if arguments['environment']:
                    res =""
                    for key,val in arguments['environment'].items():
                        res += (f'{key}={val}\n')
                    res_bytes = res.encode('utf-8')
                    self.assertEqual(
                        env,
                        res_bytes,
                        "shell does not have the right env",
                    )
                if arguments['environment'] == {} or arguments['environment'] is None:
                    self.assertEqual(
                        env,
                        b'',
                        "shell does not have the right env",
                    )

    def test_dir(self) -> None:
        """Test to see if the correct directory is used when running commands"""
        def expected_full_path(path_lib:pathlib.Path):
            expected_path = os.getcwd()
            path = str(path_lib)
            while True:
                if path.startswith('/'):
                    return path
                if path.startswith('./'):
                    path = path.removeprefix('./')
                if path.startswith('../'):
                    path = path.removeprefix('../')
                    expected_path = expected_path[:expected_path.rindex('/')]
                else:
                    if path == '':
                        return expected_path
                    expected_path = expected_path + "/" + path
                    return expected_path

        # standard arguments
        arguments_list = get_arguments_dict_list(
            {
                'current_dir':[None, pathlib.Path(__file__).parent.resolve(),pathlib.Path('/')],
                'environment':[None,{'test':'test'},{'a':'12','b':'11'},{}],
                'timeout':[None,1,10,99999999999],
                'ignore_ret_codes':[None,(1,),(1,7,),()],
            }
        )
        for arguments in arguments_list:
            # hook based argumens
            hooklist = generate_test_hook_lists(force_output=True)
            for input_hooks,output_hooks,result_hook_object in hooklist:

                # execution
                execute_command(
                        ["pwd"],
                        ordered_output_hooks=output_hooks,
                        ordered_input_hooks=input_hooks,
                        **arguments,
                    )
                if arguments['current_dir'] is None:
                    arguments['current_dir'] = './'

                curr_dir = result_hook_object.get_result()
                expected_path = expected_full_path(arguments['current_dir'])
                self.assertEqual(
                    curr_dir,
                    f'{expected_path}\n'.encode('utf-8'),
                    "the paths do not match"
                )





if __name__ == "__main__":
    unittest.main()
