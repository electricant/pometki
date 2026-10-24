# Usage: run `nix-shell` in the repository root.
{ pkgs ? import <nixpkgs> {} }:
  pkgs.mkShell {
    buildInputs = [
      (pkgs.python3.withPackages (ps: [ ps.markdown ]))
      pkgs.curl
    ];
  }
