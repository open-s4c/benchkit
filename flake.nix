{
  inputs = {
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils, ...}@inputs: flake-utils.lib.simpleFlake {
    inherit self nixpkgs;

    name = "benchkit";
    overlay =  final: prev: {
    benchkit = {
      benchkit = final.python3Packages.buildPythonPackage {
        name = "benchkit";
        src = ./.;
        doCheck = false;
      };

      benchkit-python = final.python3.withPackages (ps: [ final.benchkit.benchkit ]);
      };
    };
  };
}