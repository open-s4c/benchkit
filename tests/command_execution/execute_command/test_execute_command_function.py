import os
import pathlib
from subprocess import CalledProcessError
import unittest

from benchkit.shell.command_execution.io.stream import StringIOStream
from tests.command_execution.execute_command.util import TestTimeout, generate_test_hook_lists, get_arguments_dict_list, script_path_string, timeout
from benchkit.shell.command_execution.execute import execute_command

class FunctionalExecutionTests(unittest.TestCase):

    # @unittest.skip("disabled for debugging")
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
                try:
                # execution
                    with timeout(5):
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
                except TestTimeout:
                    self.fail(
                        "execution timed out"
                    )

    # @unittest.skip("disabled for debugging")
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
                try:
                # execution
                    with timeout(5):
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
                except TestTimeout:
                    self.fail(
                        "execution timed out"
                    )

    # @unittest.skip("disabled for debugging")
    def test_dir(self) -> None:
        """Test to see if the correct directory is used when running commands"""
        def expected_full_path(path_lib:pathlib.Path):
            expected_path = os.getcwd()
            path = str(path_lib)
            while True:
                if path.startswith('/'):
                    return path
                elif path.startswith('../'):
                    path = path.removeprefix('../')
                    expected_path = expected_path[:expected_path.rindex('/')]
                elif path.startswith('..'):
                    path = path.removeprefix('..')
                    expected_path = expected_path[:expected_path.rindex('/')]
                elif path.startswith('./'):
                    path = path.removeprefix('./')
                elif path.startswith('.'):
                    path = path.removeprefix('.')
                else:
                    if path == '':
                        return expected_path
                    expected_path = expected_path + "/" + path
                    return expected_path

        # standard arguments
        arguments_list = get_arguments_dict_list(
            {
                'current_dir':[None, pathlib.Path(__file__).parent.resolve(),pathlib.Path('/tmp'),pathlib.Path('./'),pathlib.Path('../../')],
                'environment':[None,{'test':'test'},{'a':'12','b':'11'},{}],
                'timeout':[None,1,10,99999999999],
                'ignore_ret_codes':[None,(1,),(1,7,),()],
            }
        )
        for arguments in arguments_list:
            # hook based argumens
            hooklist = generate_test_hook_lists(force_output=True)
            for input_hooks,output_hooks,result_hook_object in hooklist:
                try:
                    with timeout(5):
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
                except TestTimeout:
                    self.fail(
                        "execution timed out"
                    )


    # @unittest.skip("disabled for debugging")
    def test_input(self):
        """testing the use of the std_input parameter"""
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
                try:
                # execution
                    with timeout(5):
                        execute_command(
                        [script_path_string("writeBack")],
                        std_input=StringIOStream(f"benchkit input test {str(arguments)}\n"),
                        ordered_input_hooks=input_hooks,
                        ordered_output_hooks=output_hooks,
                        **arguments,
                        )
                    out = result_hook_object.get_result()

                    self.assertEqual(
                        out,
                        f"benchkit input test {str(arguments)}\n".encode('utf-8'),
                        f"recieved{out}",
                    )
                except TestTimeout:
                    self.fail(
                        "execution timed out"
                    )


    # @unittest.skip("disabled for debugging")
    def test_ignore_ret_codes_are_ignored(self) -> None:
        # standard arguments
        arguments_list = get_arguments_dict_list(
            {
                'current_dir':[None, pathlib.Path(__file__).parent.resolve(),pathlib.Path('/')],
                'environment':[None,{'test':'test'},{'a':'12','b':'11'},{}],
                'timeout':[None,1,10,99999999999],
                "ignore_ret_codes": [
                    (),
                    (1,4,),
                    (2, 7,),
                    (4,5,),
                    (63,),
                    (0,),
                ],
            }
        )
        for arguments in arguments_list:
            # hook based argumens
            hooklist = generate_test_hook_lists()
            for input_hooks,output_hooks,_ in hooklist:

                try:
                    with timeout(20):
                        retcode_to_output = (
                            arguments["ignore_ret_codes"][len(arguments["ignore_ret_codes"]) - 1 % 3]
                            if len(arguments["ignore_ret_codes"]) > 0
                            else 0
                        )
                        command_process = execute_command(
                            [script_path_string("returnExitCode")],
                            ordered_output_hooks=output_hooks,
                            ordered_input_hooks=input_hooks,
                            **arguments,
                            std_input=StringIOStream(f"{retcode_to_output}\n"),
                        )
                        retcode = command_process.get_return_code()
                        self.assertEqual(retcode,
                                         retcode_to_output,
                                         "Mistake in the test wrong return code was returned by programm")
                except TestTimeout:
                    self.fail(
                        "execution timed out"
                    )
                except CalledProcessError:
                    self.fail(
                        f"process trew an error with retcode {retcode_to_output} and ignored list {arguments['ignore_ret_codes']}"
                    )

    # @unittest.skip("disabled for debugging")
    def test_ignore_ret_codes_dont_ignore_other(self) -> None:
        # standard arguments
        arguments_list = get_arguments_dict_list(
            {
                'current_dir':[None, pathlib.Path(__file__).parent.resolve(),pathlib.Path('/')],
                'environment':[None,{'test':'test'},{'a':'12','b':'11'},{}],
                'timeout':[None,1,10,99999999999],
                "ignore_ret_codes": [
                    (),
                    (2, 7,),
                    (63,),
                    (0,),
                ],
                "success_value": [0, 1, 53, 19],
            }
        )
        for arguments in arguments_list:
            # hook based argumens
            hooklist = generate_test_hook_lists()
            for input_hooks,output_hooks,_ in hooklist:
                try:
                    retcode_to_output = (
                                3
                                + arguments["success_value"]
                                + (
                                    arguments["ignore_ret_codes"][len(arguments["ignore_ret_codes"]) - 1 % 3]
                                    if len(arguments["ignore_ret_codes"]) > 0
                                    else arguments["success_value"]
                                )
                            )
                    with self.assertRaises(CalledProcessError,
                                           msg=f"process did not trow an error with retcode {retcode_to_output}, ignored list {arguments['ignore_ret_codes']} and succes value {arguments['success_value']}"):
                        with timeout(20):
                            command_process = execute_command(
                                [script_path_string("returnExitCode")],
                                ordered_output_hooks=output_hooks,
                                ordered_input_hooks=input_hooks,
                                **arguments,
                                std_input=StringIOStream(f"{retcode_to_output}\n"),
                            )
                            retcode = command_process.get_return_code()
                            self.assertEqual(retcode,
                                            retcode_to_output,
                                            "Mistake in the test wrong return code was returned by programm")
                except TestTimeout:
                    self.fail(
                        "execution timed out"
                    )

if __name__ == "__main__":
    unittest.main()
