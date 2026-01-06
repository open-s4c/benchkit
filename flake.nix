{
  description = "Minimal flake for benchkit";
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-25.11";
    pythainer.url = "git+https://github.com/EstAK/pythainer.git?ref=nixos";
    dream2nix.url = "github:nix-community/dream2nix";
  };

  outputs = {
    self,
    nixpkgs,
    dream2nix,
    pythainer
  }:
    let
      eachSystem = nixpkgs.lib.genAttrs [
        "aarch64-darwin"
        "aarch64-linux"
        "x86_64-darwin"
        "x86_64-linux"
      ];
    in {

      packages = eachSystem (system : {
        default = dream2nix.lib.evalModules {
          packageSets.nixpkgs = nixpkgs.legacyPackages.${system};
          modules = [
            .nix/default.nix
            {
              paths.lockFile = ".nix/lock.${system}.json";
              paths.projectRoot = ./.; 
              paths.projectRootFile = "flake.nix"; 
              paths.package = ./.;
            }
          ];
        };
      });


      devShells = eachSystem (system:
        let
          pkgs = nixpkgs.legacyPackages.${system}; # 
          benchkit = self.packages.${system}.default;
          python = benchkit.config.deps.python;
        in {
          default = pkgs.mkShell { # 
            inputsFrom = [benchkit.devShell]; # 
            packages = [

              benchkit.config.deps.pythainerPackage
              benchkit.config.deps.qemu_full
              benchkit.config.deps.tmux

              python.pkgs.python-lsp-ruff
              python.pkgs.pip

              pkgs.ruff 
              pkgs.black
            ];
          };
        });

    };
}
