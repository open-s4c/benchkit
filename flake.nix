{
  description = "Minimal flake for benchkit";
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-25.11";
    flake-utils.url = "github:numtide/flake-utils";
    pythainer.url = "git+https://github.com/EstAK/pythainer.git?ref=nixos";
  };

  outputs = { self, nixpkgs, flake-utils, pythainer, ... }:

    flake-utils.lib.eachDefaultSystem (system : 
      let
  	    pkgs = import nixpkgs {inherit system;};
	      python = pkgs.python3;
	      pythonPackages = pkgs.python3Packages;
        pythainerEnv = pythainer.packages.${system}.pythainerEnv;
 	      pythonEnv = python.withPackages (ps: with ps; [
   	      pip
          matplotlib
          pandas
          seaborn
	        docopt
          libtmux # this is only required for the tmux extension : make it another lib ?
          gitpython
          wget
        ]);
        pythainerPackage = pythainer.packages.${system}.pythainer;
      in
        {
	        packages.benchkit = pythonPackages.buildPythonPackage {
            pname = "pybenchkit";
  	        version = "0.0.1";

            src = ./.;
	          propagatedBuildInputs = [
	            pythonEnv
              pythainerPackage
            ];

            format = "pyproject";
  	        build-system = [ pythonPackages.hatchling ];
	        };
          packages.default = self.packages.${system}.benchkit;
          devShells.default = pkgs.mkShell {
            packages = with pkgs; [
	            self.packages.${system}.benchkit
              isort
              black
              pyright
              qemu_full
            ];
          };

        }
    );
}
