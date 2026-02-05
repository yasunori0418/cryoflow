{
  description = "cryoflow development environment";

  inputs = {
    root = {
      url = "path:../";
      inputs.nixpkgs.follows = "nixpkgs";
      inputs.flake-parts.follows = "flake-parts";
    };

    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-parts.url = "github:hercules-ci/flake-parts";
  };

  outputs =
    inputs@{ flake-parts, ... }:
    flake-parts.lib.mkFlake { inherit inputs; } {
      imports = [ ];
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
          inputs',
          pkgs,
          # system,
          ...
        }:
        let
          # https://pyproject-nix.github.io/uv2nix/usage/getting-started.html#setting-up-a-development-environment-optional
          # Access workspace and pythonSet from root via legacyPackages
          rootWorkspace = inputs'.root.legacyPackages.workspace;
          rootPythonSet = inputs'.root.legacyPackages.pythonSet;
          editableOverlay = rootWorkspace.mkEditablePyprojectOverlay {
            # Use environment variable pointing to editable root directory
            root = "$REPO_ROOT";
            # Optional: Only enable editable for these packages
            # members = [ "hello-world" ];
          };
          editablePythonSet = rootPythonSet.overrideScope (
            pkgs.lib.composeManyExtensions [
              editableOverlay
              (
                final: prev:
                let
                  addEditables =
                    name:
                    prev.${name}.overrideAttrs (old: {
                      nativeBuildInputs = (old.nativeBuildInputs or [ ]) ++ [
                        final.editables
                      ];
                    });
                in
                {
                  cryoflow = addEditables "cryoflow";
                  cryoflow-core = addEditables "cryoflow-core";
                  cryoflow-plugin-collections = addEditables "cryoflow-plugin-collections";
                }
              )
            ]
          );
          virtualenv = editablePythonSet.mkVirtualEnv "cryoflow-dev-env" rootWorkspace.deps.all;
        in
        {
          devShells.default = pkgs.mkShell {
            inputsFrom = [ inputs'.root.packages.default ];
            packages =
              with pkgs;
              [
                uv
                ruff
                pyright
              ]
              ++ [ virtualenv ];
            env = {
              UV_PYTHON_PREFERENCE = "only-system";
              UV_NO_SYNC = "1";
              UV_PYTHON = editablePythonSet.python.interpreter;
              UV_PYTHON_DOWNLOADS = "never";
            };
            shellHook = ''
              unset PYTHONPATH
              export REPO_ROOT=$(git rev-parse --show-superproject-working-tree --show-toplevel)
            '';
          };
        };
    };
}
