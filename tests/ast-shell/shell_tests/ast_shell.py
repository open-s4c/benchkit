from itertools import product
import pathlib
import sys
import unittest
import unittest.mock
import io

from benchkit.shell.ast_shell_out import shell_out_new
from shell_scripts import script_path_string, timeout

import re

import unittest.mock

import tracemalloc

tracemalloc.start()



# Due to print statements being inside of threads unittest does not allow us to check the output of stdout.
# We will have to write tests in a different way to check what the user sees.
# To this end these tests only test functionality

class BasicShellTests(unittest.TestCase):
    def test_echo(self):

        options = ["redirect_stderr_to_stdout","current_dir","environment","print_output","timeout","output_is_log","ignore_ret_codes"]
        redirect_stderr_to_stdout = [True,False]
        current_dir = [None, pathlib.Path(__file__).parent.resolve()]
        environment = [None,{"test":"test"}]
        print_output = [False,True]
        timeout = [None,20]
        output_is_log = [False,True]
        ignore_ret_codes = [(),(1,)]
        res = list(product(redirect_stderr_to_stdout,current_dir,environment,print_output,timeout,output_is_log,ignore_ret_codes))
        for perm in res:
            args = dict(zip(options, perm))
            # test echo with multiple parameters to make sure none mess up the result
            a = shell_out_new(
                f"echo benchkit_echo_test {str(perm)}",
                print_command=True,
                **args
            )
            expeced_result = re.sub(r'\'', '', f"benchkit_echo_test {str(perm)}")
            self.assertEqual(a,f"{expeced_result}\n","shell does not provide the right output in the result")

    def test_run_forever(self):
        with self.assertRaises(Exception):
            with timeout(5):
                shell_out_new(f"{script_path_string("runForever")}",output_is_log=True,redirect_stderr_to_stdout=False)



if __name__ == '__main__':
    unittest.main()