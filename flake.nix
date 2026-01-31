{
  description = "Plug-in-driven column-oriented data processing CLI tool with Polars LazyFrame at its core.";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-parts.url = "github:hercules-ci/flake-parts";

    # Tool for interpreting `uv.lock` on Nix
    pyproject-nix = {
      url = "github:pyproject-nix/pyproject.nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    uv2nix = {
      url = "github:pyproject-nix/uv2nix";
      inputs.pyproject-nix.follows = "pyproject-nix";
    };

    # Build system support
    pyproject-build-systems = {
      url = "github:pyproject-nix/build-system-pkgs";
      inputs.nixpkgs.follows = "nixpkgs";
      inputs.pyproject-nix.follows = "pyproject-nix";
    };
  };

  outputs =
    inputs@{ flake-parts, ... }:
    flake-parts.lib.mkFlake { inherit inputs; } {
      imports = [
        # To import an internal flake module: ./other.nix
        # To import an external flake module:
        #   1. Add foo to inputs
        #   2. Add foo as a parameter to the outputs function
        #   3. Add here: foo.flakeModule

      ];
      systems = [
        "x86_64-linux"
        "aarch64-linux"
        "aarch64-darwin"
        "x86_64-darwin"
      ];
      perSystem =
        {
          # config,
          # self',
          # inputs',
          pkgs,
          # system,
          ...
        }:
        {
          packages =
            let
              # 1. Load project metadata
              workspace = inputs.uv2nix.lib.workspace.loadWorkspace { workspaceRoot = ./.; };

              # 2. Specifying Python interpreter
              python = pkgs.python314;

              # 3. Generate Nix overlay from `uv.lock`
              overlay = inputs.uv2nix.lib.workspace.mkOverlay {
                inherit workspace;
              };

              # 4. Building a Python package set
              pythonSet = python.pkgs.overrideScope (
                pkgs.lib.composeManyExtensions [
                  inputs.pyproject-build-systems.overlays.default
                  overlay
                ]
              );
            in
            {
              default =
                (pythonSet.mkPythonEditablePackage {
                  root = ./.;
                }).packages;
            };
        };
    };
}
