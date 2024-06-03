{
  inputs = {
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils, ...}@inputs: flake-utils.lib.simpleFlake {
    inherit self nixpkgs;

    name = "benchkit";
    overlay =  final: prev: {
    benchkit = {
      benchkit = let
         pythonPackages = final.python3Packages;
      in pythonPackages.buildPythonPackage {
        name = "benchkit";
        src = ./.;
        doCheck = false;
        dependencies = with pythonPackages; [matplotlib pandas seaborn];
      };

      benchkit-python = final.python3.withPackages (ps: [ final.benchkit.benchkit ]);
      };
    };
  };
}
