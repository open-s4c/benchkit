# Installing benchkit using Nix

To start working with benchkit, you can run the following command:
```sh
nix develop github:open-s4c/benchkit
```
This command will open a new shell which contains a python with benchkit and its dependencies installed,
allowing you to run any benchkit project by running the benchmarking file using python.

## Running benchkit projects

The benchkit flake currently implements three benchmarks that from the `tutorials/` folder you can run,
these benchmarks are `libvsync_locks`, `leveldb` and `leveldb_perf`, running these benchmarks can be done using the
following command:
```
nix run github:open-s4c/benchkit#<benchmark>
```

## Using benchkit in a custom flake

To use benchkit in your own flake, you will first have to import it:
```nix
inputs.benchkit.url = "github:open-s4c/benchkit"
inputs.benchkit.inputs.nixpkgs.follows = "nixpkgs"
```

Afterwards you can access the benchkit derivation like this:
```nix
benchkit.packages.${system}.benchkit
```
This derivation is a python package that should be when installing python like this: 
```nix
pkgs.python.withPackages (pks: [ benchkit ])
```

If you want to build your own benchmark in Nix, you can do this using the `buildBencmark` function that is added to the benchkit derivation:
```nix
benchkit.packages.${system}.benchkit.buildBenchkit {
    name = "myBenchmark";
    src = ./.;
}
```
This function will create a new derivation which contains a program that, when run, will execute your benchmark.
This function has the following arguments:
* `name`
    * The name of your benchmark.
* `src`
    * The source directory of your benchmark, this should include both your Python benchmark file, and the code that you want to benchmark.
* `extraPythonPackages`
    * default: `[]`
    * Extra Python packages that should be used when running the benchmark.
* `benchmark`
    * default: `benchmark.py`
    * The name of the benchmark Python file that, relative to the `src` directory, this the entry file of your benchmark.
* `replaceBenchmarkSrcDir`
    * default: `false`
    * Replace the value of the variable in `benchmarkSrcDirVariable` with the path to your benchmarking code in the Nix store. This means that, if `benchmarkSrcDirVariable` is `_bench_src_path` and `benchmarkSrcDir` is `src/`, then `_bench_src_path = <filepath>` will be replaced with `_bench_src_path = <Nix store filepath>/src`, this substitution will be done in `dirsFile`.
    * This is used in case the path you are using for your benchmarking directory is not one that would find the Nix store.
        * If you are using `get_curdir(__file__)`, then this can remain `false`
* `benchmarkSrcDirVariable`
    * default: `_bench_src_path`
    * The variable for which to replace the value in the Nix store, see `replaceBenchmarkSrcDir`.
* `benchmarkSrcDir`
    * default: `"."`
    * The directory in which your benchmarking code is, relative to the root directory given to by `src`, see `replaceBenchmarkSrcDir`.
* `replaceBuildDir`
    * default: `false`
    * Replace the value of the variable in `buildDirVariable` with the `buildDir`. This means that, if `buildDirVariable` is `_build_dir` and `buildDir` is `./build`, then `_build_dir = <filepath>` will be replaced with `_build_dir = "./build"`, this substitution will be done in `dirsFile`.
* `buildDirVariable`
    * default: `_build_dir`
    * The variable for which to replace the value to `buildDir`, see `replaceBuildDir`.
* `buildDir`
    * default: `"./build/build_${name}"`
    * The directory in which your benchmark should be compiled, this is only used when `replaceBuildDir` is `true`, see `replaceBuildDir`.
* `dirsFile`
    * default: value of the `benchmark` variable
    * The file in which the build directory and benchmark source directory should be replaced, see `replaceBenchmarkSrcDir` and `replaceBuildDir`.
* `useSudo`
    * default: `false`
    * Whether or not `sudo` should be added to the path.
* All the arguments allowed by `stdenv.mkDerivation`
    * e.g. `buildInptus`
