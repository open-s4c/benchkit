{
  # The current NixPkgs release
  inputs.nixpkgs.url = "github:nixos/nixpkgs/nixos-24.11";

  outputs =
    { nixpkgs, ... }:
    let
      supportedSystems = [
        "x86_64-linux"
        "x86_64-darwin"
        "aarch64-linux"
        "aarch64-darwin"
      ];
      /**
        Run the given function for all the systems in `supportedSystems`.

        # Example

        ```nix
        forAllSystems (system: pkgs: {packages.default = pkgs.coreutils;})
        =>
        {
           packages = {
              x86_64-linux.default = pkgs.coreutils;
              x86_64-darwin.default = pkgs.coreutils;
              aarch64-linux.default = pkgs.coreutils;
              aarch64-darwin.default = pkgs.coreutils;
           };
        };
        ```

        # Type

        ```
        forAllSystems :: (String -> { ... } -> { ... }) -> { ... }
        ```
      */
      forAllSystems =
        f:
        nixpkgs.lib.foldr nixpkgs.lib.recursiveUpdate { } (
          nixpkgs.lib.forEach supportedSystems (
            system:
            builtins.mapAttrs (name: value: { ${system} = value; }) (f system nixpkgs.legacyPackages.${system})
          )
        );
    in
    forAllSystems (
      system: pkgs:
      let
        # The version of benchkit
        version = "0.0.1";
        # The version of python to use
        python = pkgs.python3;
        # The Linux kernel to use, this is used for packages like `perf`
        # Uses the latest LTS release (as of 2025-03-12)
        # NOTE: This should be updated when a new LTS version is released
        linuxKernel = pkgs.linuxKernel.packages.linux_6_12;
        # From where to get the python packages, these are packages like `numpy`, `matplotlib`, ...
        pythonPackages = pkgs.python3Packages;
        # The main benchkit python package
        benchkit = pythonPackages.buildPythonPackage {
          inherit version;
          pname = "pybenchkit";
          src = ./.;
          propagatedBuildInputs = [
            pythonPackages.matplotlib
            pythonPackages.pandas
            pythonPackages.seaborn
            pythonPackages.hatchling
          ];
          # Use a `pyproject.toml` file
          format = "pyproject";
        };
        /**
          Make a derivation for a benchmark using the [benchkit](https://github.com/open-s4c/benchkit)

          # Type

          ```nix
          buildBenchmark ::
            name :: String;
            src :: String | Path;
            extraPythonPackages :: ({...} -> [{...}]) ? (_: [ ]);
            benchmark :: String ? "benchmark.py";
            replaceBenchmarkSrcDir :: Bool ? false;
            benchmarkSrcDirVariable :: String ? "_bench_src_path";
            benchmarkSrcDir :: String ? ".";
            replaceBuildDir :: Bool ? false;
            buildDirVariable :: String ? "_build_dir";
            buildDir :: String ? "./build/build_${name}";
            dirsFile :: String ? benchmark;
            useSudo :: Bool ? false,
            } // Derivation -> {...}
          ```

          # Arguments

          name
          : The name of your benchmark.

          src
          : The source directory of your benchmark, this should include both your Python benchmark file,
            and the code that you want to benchmark.

          extraPythonPackages
          : Extra Python packages that should be used when running the benchmark.

          benchmark
          : The name of the benchmark Python file that, relative to the `src` directory,
            this the entry file of your benchmark.

          replaceBenchmarkSrcDir
          : Replace the value of the variable in `benchmarkSrcDirVariable` with the path
            to your benchmarking code in the Nix store.
            This means that, if `benchmarkSrcDirVariable` is `_bench_src_path` and `benchmarkSrcDir`
            is `src/`, then `_bench_src_path = <filepath>` will be replaced with
            `_bench_src_path = <Nix store filepath>/src`, this substitution will be done in `dirsFile`.

          benchmarkSrcDirVariable
          : The variable for which to replace the value in the Nix store, see `replaceBenchmarkSrcDir`.

          benchmarkSrcDir
          : The directory in which your benchmarking code is, relative to the root directory given to by `src`,
            see `replaceBenchmarkSrcDir`.

          replaceBuildDir
          : Replace the value of the variable in `buildDirVariable` with the `buildDir`.
            This means that, if `buildDirVariable` is `_build_dir` and `buildDir`
            is `./build`, then `_build_dir = <filepath>` will be replaced with
            `_build_dir = "./build"`, this substitution will be done in `dirsFile`.

          buildDirVariable
          : The variable for which to replace the value to `buildDir`, see 'replaceBuildDir'.

          buildDir
          : The directory in which your benchmark should be compiled, this is only used when `replaceBuildDir` is `true`,
            see 'replaceBuildDir'.

          dirsFile
          : The file in which the build directory and benchmark source directory should be replaced,
            see `replaceBenchmarkSrcDir` and `replaceBuildDir`.

          useSudo
          : Whether or not `sudo` should be added to the path.
        */
        buildBenchmark =
          {
            name,
            src,
            extraPythonPackages ? (_: [ ]),
            buildInputs ? [ ],
            nativeBuildInputs ? [ ],
            benchmark ? "benchmark.py",
            replaceBenchmarkSrcDir ? false,
            benchmarkSrcDirVariable ? "_bench_src_path",
            benchmarkSrcDir ? ".",
            replaceBuildDir ? false,
            buildDirVariable ? "_build_dir",
            buildDir ? "./build/build_${name}",
            dirsFile ? benchmark,
            useSudo ? false,
            ...
          }@attrs:
          let
            benchPython = python.withPackages (pks: [ benchkit ] ++ extraPythonPackages pks);
            bin = pkgs.writeShellScript "benchmark_${name}" ''${pkgs.lib.getExe benchPython} "@out@/${benchmark}"'';
            attrNames = [
              "name"
              "src"
              "extraPythonPackages"
              "buildInputs"
              "nativeBuildInputs"
              "benchmark"
              "replaceBenchmarkSrcDir"
              "benchmarkSrcDirVariable"
              "benchmarkSrcDir"
              "replaceBuildDir"
              "buildDirVariable"
              "buildDir"
              "dirsFile"
              "useSudo"
            ];
          in
          pkgs.stdenv.mkDerivation
          <|
            builtins.removeAttrs attrs attrNames
            // {
              name = "benchmark_" + name;
              src = src;
              nativeBuildInputs = nativeBuildInputs ++ [ pkgs.makeWrapper ];
              postPatch =
                # There are some paths that need to be changed, since the source code of the benchmark is in
                # the Nix store, where to program wouldn't be able to find it normally,
                # and the build folder should be done locally, since the Nix store is immutable.
                pkgs.lib.optionalString (replaceBenchmarkSrcDir || replaceBuildDir) (
                  "\nsubstituteInPlace '${dirsFile}'"
                  + pkgs.lib.optionalString replaceBenchmarkSrcDir " --replace-warn '${benchmarkSrcDirVariable} = ' \"${benchmarkSrcDirVariable} = pathlib.Path('$out/${benchmarkSrcDir}') #\""
                  + pkgs.lib.optionalString replaceBuildDir " --replace-warn '${buildDirVariable} = ' '${buildDirVariable} = pathlib.Path(\"${buildDir}\") #'"
                );
              installPhase = ''
                runHook preInstall

                mkdir -p "$out/bin"
                cp -r * "$out/"
                substitute "${bin}" "$out/bin/benchmark_${name}" --replace-fail "@out@" "$out"
                chmod +x "$out/bin/benchmark_${name}"
                wrapProgram "$out/bin/benchmark_${name}" --set PATH ${
                  pkgs.lib.makeBinPath
                  <|
                    buildInputs
                    ++ [
                      pkgs.coreutils
                      pkgs.nettools
                      pkgs.git
                      pkgs.which
                    ]
                    ++ (pkgs.lib.optional useSudo "/run/wrappers/")
                }

                runHook postInstall
              '';
              meta.mainProgram = "benchmark_" + name;
              dontBuild = true;
            };
        # ======== TUTORIALS ========
        /**
          This is a wrapper for `buildBenchmark` that makes it easier to build the tutorials included in `benchkit`

          # Type

          ```nix
          buildTutorial :: {
            deps :: { [ depName :: String ] :: String | Path } ? { };
            depsInTopLevelDir :: Bool ? false;
            importKit :: { [ name :: String ] :: String } ? { };
            benchmarkSrcDir :: String;
          } // buildBenchmark // Derivation -> {...}
          ```

          # Arguments

          deps
          : The dependencies that are used for this tutorial, this should be an attribute set,
            with as key the name of the dependency, and as value the path to the source code.
            Any dependency, here will be symlinked into either `benchmarkSrcDir/deps/depName`, or `deps/depName`
            depending on `depsInTopLevelDir`.

          depsInTopLevelDir
          : If true, place `dep` folder, the dependencies from the `deps` argument in the top level directory, otherwise place it in `benchmarkSrcDir` directory

          importKit
          : Most tutorials use a `kit` directory which is added to the python path at the top level,
            because of this references to these files usually have to be prefixed with `.kit`, this is
            done by this variable.
            To do this, you give a attribute set that maps files, relative to the source directory,
            to a list of imports in that file, every input in this list will then be prefixed with `.kit`.
            This means that the following Nix code would replace `import vsyncmicrobench` in the file
            `campaign_locks.py` with `import kit.vsyncmicrobench`.
            ```nix
            importKit = { "campaign_locks.py" = [ "vsyncmicrobench" ]; };
            ```

          benchmarkSrcDir
          : The directory in which your benchmarking source files are located
        */
        buildTutorial =
          {
            deps ? { },
            depsInTopLevelDir ? false,
            importKit ? { },
            benchmarkSrcDir,
            postInstall ? "",
            prePatch ? "",
            buildInputs ? [ ],
            ...
          }@attrs:
          buildBenchmark
          <|
            builtins.removeAttrs attrs [
              "deps"
              "depsInTopLevelDir"
              "importKit"
              "buildInputs"
              "postInstall"
            ]
            // {
              replaceBuildDir = true;
              buildInputs = [
                pkgs.cmake
                pkgs.gnumake
                pkgs.gcc
              ] ++ buildInputs;
              prePatch =
                pkgs.lib.foldlAttrs (
                  acc: file: importModules:
                  acc
                  + (pkgs.lib.foldr (
                    importModule: acc: acc + " --replace-fail 'from ${importModule}' 'from kit.${importModule}'"
                  ) "\nsubstituteInPlace '${file}'" importModules)
                ) "" importKit
                + "\n"
                + prePatch;
              postInstall =
                ''mkdir -p "$out/${pkgs.lib.optionalString (!depsInTopLevelDir) "${benchmarkSrcDir}/"}deps"''
                + pkgs.lib.foldlAttrs (
                  acc: dep: src:
                  acc
                  + "\nln -s ${src} \"$out/${
                    pkgs.lib.optionalString (!depsInTopLevelDir) "${benchmarkSrcDir}/"
                  }deps/${dep}\""
                ) "" deps
                + "\n"
                + postInstall;
              dontConfigure = true;
            };
        tutorials = {
          # A library of synchronization primitives that is used in the benchmarks of some tutorials,
          # only the source is here since `benchkit` expects source code so it can compile the program
          # with differing options
          libvsync-src = pkgs.fetchFromGitHub {
            rev = "refs/tags/v4.1.0";
            owner = "open-s4c";
            repo = "libvsync";
            hash = "sha256-Sb1sbs5TnGyD2vxaDRUbCQjpYAHeu3zWo9ft3evXpV0=";
          };
          leveldb-src = pkgs.stdenv.mkDerivation {
            name = "leveldb-src";
            src = pkgs.fetchFromGitHub {
              rev = "068d5ee1a3ac40dabd00d211d5013af44be55bea";
              owner = "google";
              repo = "leveldb";
              fetchSubmodules = true;
              hash = "sha256-D12hjWT80YMwliVqNtryZkA1US0JUhtDFT9xBm9o8ng=";
            };
            patches = [ ./tutorials/leveldb-bench/patch.diff ];
            buildPhase = ''
              runHook preBuild

              mkdir -p "$out"
              mv * "$out"

              runHook postBuild
            '';
            dontConfigure = true;
          };
          # The [lybvsync locks](tutorials/libvsync-locks/README.md) tutorial
          libvsync-locks = buildTutorial {
            name = "tutorial_libvsync-locks";
            src = tutorials/libvsync-locks;
            benchmarkSrcDir = "microbench/";
            benchmark = "campaign_locks.py";
            dirsFile = "kit/vsyncmicrobench.py";
            deps = {
              "libvsync" = tutorials.libvsync-src;
            };
            importKit = {
              "campaign_locks.py" = [ "vsyncmicrobench" ];
            };
          };
          leveldb-opts = {
            src = tutorials/leveldb-bench;
            benchmarkSrcDir = "deps/leveldb";
            deps = {
              "leveldb" = tutorials.leveldb-src;
            };
            depsInTopLevelDir = true;
            dirsFile = "leveldb.py";
            prePatch = "cp ${./examples/leveldb/kit/leveldb.py} 'leveldb.py'";
          };
          leveldb =
            buildTutorial
            <|
              tutorials.leveldb-opts
              // {
                name = "tutorial_leveldb";
                benchmark = "campaign_leveldb.py";
              };
          leveldb_perf =
            buildTutorial
            <|
              tutorials.leveldb-opts
              // {
                name = "tutorial_leveldb_perf";
                buildInputs = [
                  pkgs.procps
                  # Use latest LTS release
                  linuxKernel.perf
                ];
                useSudo = true;
                benchmark = "campaign_leveldb_perf.py";
              };
        };
      in
      {
        packages =
          let
            buildableBenchkit = benchkit // {
              inherit buildBenchmark;
            };
          in
          {
            default = buildableBenchkit;
            benchkit = buildableBenchkit;
          };
        apps = rec {
          default = libvsync-locks;
          libvsync-locks = {
            type = "app";
            program = "${pkgs.lib.getExe tutorials.libvsync-locks}";
          };
          leveldb = {
            type = "app";
            program = "${pkgs.lib.getExe tutorials.leveldb}";
          };
          leveldb_perf = {
            type = "app";
            program = "${pkgs.lib.getExe tutorials.leveldb_perf}";
          };
        };
        devShells.default = pkgs.mkShell {
          packages = [
            pkgs.pyright
            (python.withPackages (_: [ benchkit ]))
            tutorials.libvsync-locks
          ];

        };
      }
    );
}
