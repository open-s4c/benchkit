{
  config,
  lib,
  dream2nix,
  pkgs,
  pythainer,
  ...
}: let
  pyproject = lib.importTOML (config.mkDerivation.src + /pyproject.toml);
in {
  
  imports = [
    dream2nix.modules.dream2nix.pip
  ];

  # package dependencies
  deps = { nixpkgs, pythainer, ... } : {

    python = nixpkgs.python3;
    pythainerPackage = pythainer.default;
    inherit
      (nixpkgs)
      qemu_full
      tmux
      git
    ;
  };

  inherit (pyproject.project) name version;

  mkDerivation = {
    nativeBuildInputs = [];

    propagatedBuildInputs = [
      config.deps.qemu_full
      config.deps.tmux
      config.deps.git
      config.deps.pythainerPackage
    ];

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
    # concatenate both the build system (above) and the requirements.txt
    requirementsList =
      pyproject.build-system.requires or [] 
      ++  pyproject.project.dependencies or [];
    requirementsFiles = ["requirements.txt"];
    flattenDependencies = true;

    # this is required as the pypi version of docopt makes the build fail
    overrides.docopt = {
        buildPythonPackage.pyproject = true;
        mkDerivation.buildInputs = [config.deps.python.pkgs.setuptools];
    };

    overrides.wget = {
        buildPythonPackage.pyproject = true;
        mkDerivation.buildInputs = [config.deps.python.pkgs.setuptools];
    };
  };


}
