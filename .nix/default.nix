{
  config,
  lib,
  dream2nix,
  pkgs,
  ...
}: let
  pyproject = lib.importTOML (config.mkDerivation.src + /pyproject.toml);
in {
  
  imports = [
    dream2nix.modules.dream2nix.pip
  ];

  # package dependencies
  deps = {
    nixpkgs,
    ...
  } : {

    python = nixpkgs.python3;
    inherit (nixpkgs);
  };

  inherit (pyproject.project) name version;

  mkDerivation = {
    nativeBuildInputs = [
      pkgs.hostname
    ];

    propagatedBuildInputs = [];

    src = lib.cleanSourceWith {
      src = lib.cleanSource ./..;
      filter = name : type:
        !(builtins.any (x: x) [
          (lib.hasSuffix ".nix" name) # do not package nix files
          (lib.hasPrefix "." (builtins.baseNameOf name)) # do not package hidden files
          (lib.hasSuffix "flake.lock" name) # do not include the flake lock
        ]);
    };
  };

  buildPythonPackage = {
    pyproject = true; 
    pythonImportsCheck = [ # checks that python can import pythainer
      "benchkit" 
      "pythainer"
    ];
  };

  pip = {
    requirementsList =
      pyproject.build-system.requires or []
      ++ pyproject.project.dependencies or []
      ++ [
        # every dependency that is needed by benchkit and not specified in pyproject.toml should be added here
        "numpy"
        "pyserial"
        "git+https://github.com/apaolillo/pythainer.git"
      ];

    flattenDependencies = true;

    overrides.pythainer = {
      buildPythonPackage.pyproject = true;
      mkDerivation.nativeBuildInputs = [ config.deps.python.pkgs.hatchling ];
    };

    overrides.docopt = {
      buildPythonPackage.pyproject = true;
      mkDerivation.buildInputs = [ config.deps.python.pkgs.setuptools ];
    };

    overrides.wget = {
      buildPythonPackage.pyproject = true;
      mkDerivation.buildInputs = [ config.deps.python.pkgs.setuptools ];
    };
  };
}
