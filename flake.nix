{
  description = "Minimal flake for benchkit";
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-25.11";
    pythainer.url = "github:apaolillo/pythainer";
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
          packageSets.pythainer = pythainer.packages.${system};
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
          pkgs = import nixpkgs {inherit system;};
          benchkit = self.packages.${system}.default;
          python = benchkit.config.deps.python;

          benchkitCorePackages = [
            benchkit.config.deps.pythainerPackage
            benchkit.config.deps.stress-ng
            benchkit.config.deps.tmux
          ];

          pythonToolingPackages = [
            python.pkgs.python-lsp-ruff
            python.pkgs.numpy
            python.pkgs.pip
          ];

          formattingPackages = [
            python.pkgs.flake8
            pkgs.pylint
            pkgs.isort
            pkgs.black
            pkgs.ruff 
          ];
        in {
          core = pkgs.mkShell { # 
            inputsFrom = [benchkit.devShell]; # 
            packages = benchkitCorePackages
                       ++ pythonToolingPackages
                       ++ formattingPackages
                       ++ [];
          };

          # example of a devshell where non free software is required
          # unfree = pkgs.mkShell {
          #   inputsFrom = [self.devShells.${system}.core];
          #   packages = let
          #     pkgs = import nixpkgs {
          #       inherit system;
          #       config.allowUnfree = true;
          #     };
          #   in benchkitCorePackages
          #      ++ pythonToolingPackages
          #      ++ formattingPackages
          #      ++ [];
          # };

          default = self.devShells.${system}.core;
        });
    };
}
