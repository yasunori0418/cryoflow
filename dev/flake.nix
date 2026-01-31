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
        {
          devShells.default = pkgs.mkShell {
            inputsFrom = [ inputs'.root.packages.default ];
            packages = with pkgs; [
              uv
              ruff
              pyright
            ];
            UV_PYTHON_PREFERENCE = "only-system";
          };
        };
    };
}
