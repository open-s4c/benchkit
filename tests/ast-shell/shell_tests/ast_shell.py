import unittest
import unittest.mock
import io
from benchkit.shell.ast_shell_out import shell_out_new
from shell_scripts import script_path_string
import tracemalloc

tracemalloc.start()



class BasicShellTests(unittest.TestCase):
    
    @unittest.mock.patch('sys.stdout', new_callable=io.StringIO)
    def test_echo(self,mock_stdout):
            a = shell_out_new(
                "echo benchkit_echo_test",output_is_log=True ,redirect_stderr_to_stdout=False,
            )
            self.assertEqual(a,"benchkit_echo_test\n","shell does not provide the right output in the result")
            f = open("demofile2.txt", "a")
            print("yeet")
            f.write(mock_stdout.getvalue())
            f.write("b")
            f.close()




def test():

    # THE TWO EXAMPLES BELOW DONT HALT
    # They exist to show that functions work in an intuative manner.

    a = shell_out_new(
        script_path_string("waitThenPrint"), print_output=True, output_is_log=True, redirect_stderr_to_stdout=False,run_in_background=True
    )
    print(f"test{a} -------------------------------------------------------------")
    a = shell_out_new(
        "ls", print_output=True, output_is_log=True, redirect_stderr_to_stdout=False,
    )

    print("--------------------")
    print(a)

    # To show that output is log works
    # a = shell_out_new(
    #     "cat /dev/random", print_output=True, output_is_log=True
    # )
    # print("--------------------")
    # print(a)
    # To show that input works
    # shell_out_new(
    #     "ssh user@host -p 22 'cat'", output_is_log=True, std_input="wafel\n" \
    #     "aeu aeu\n"
    # )


    # a = shell_out_new(
    #     "ssh user@host -p 22 'perf stat sleep 1'", print_output=True, output_is_log=True,redirect_stderr_to_stdout=False
    # )
    # print("--------------------")
    # print(a)
    # shell_out_new(["ssh", "user@host", "-p", "57429", "-t", "perf stat sleep 1"])
    # main_command_ast = makecommand.command("sleep", ["1"])
    # full_command = makecommand.command("perf stat", [inline(main_command_ast)])
    # remote_command = execute_on_remote(full_command, "user@host", port=57429)
    # shell_out_new(remote_command)


if __name__ == "__main__":
    # commandtests()
    # localtests()
    # newtest()
    # runtest()
    test()
