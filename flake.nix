# SPDX-FileCopyrightText: 2024 Kartoza <info@kartoza.com>
# SPDX-License-Identifier: AGPL-3.0-or-later
{
  description = "Cloud Native GIS - Django platform for serving vector and raster geospatial layers";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};

        # Python with packages
        pythonEnv = pkgs.python312.withPackages (ps: with ps; [
          # Django and web
          django
          djangorestframework
          django-cors-headers
          psycopg2

          # GIS
          geopandas
          fiona
          shapely
          pyproj

          # Development tools
          pytest
          pytest-cov
          pytest-django
          factory-boy
          black
          isort
          mypy
          pre-commit

          # Documentation
          mkdocs
          mkdocs-material

          # Release tools
          build
          twine
          setuptools
          wheel
        ]);

        # Common build inputs
        commonBuildInputs = with pkgs; [
          # Python environment
          pythonEnv

          # Development tools
          ruff
          pre-commit
          reuse
          just
          git
          gh
          git-cliff
          commitizen

          # GIS tools
          gdal
          geos
          proj

          # Database
          postgresql
          postgis

          # Docker
          docker
          docker-compose

          # Node.js for frontend
          nodejs_20
          nodePackages.npm
          nodePackages.prettier

          # Documentation
          mkdocs

          # Utilities
          jq
          yq
          curl
          wget
        ];

      in
      {
        # Development shell
        devShells.default = pkgs.mkShell {
          buildInputs = commonBuildInputs;

          shellHook = ''
            echo "Cloud Native GIS Development Environment"
            echo "========================================"
            echo ""
            echo "Available commands:"
            echo "  just          - Task runner (run 'just' to see all tasks)"
            echo "  nix run .#    - Run Nix apps (use tab completion)"
            echo ""
            echo "Python: $(python --version)"
            echo "Node: $(node --version)"
            echo ""

            # Set up Python path for Django
            export PYTHONPATH="$PWD/django_project:$PYTHONPATH"

            # Set up pre-commit if not already done
            if [ ! -f .git/hooks/pre-commit ]; then
              echo "Installing pre-commit hooks..."
              pre-commit install --install-hooks || true
            fi
          '';
        };

        # Nix apps for common tasks
        apps = {
          # Documentation
          docs = {
            type = "app";
            program = toString (pkgs.writeShellScript "docs" ''
              cd docs
              ${pkgs.mkdocs}/bin/mkdocs serve -f mkdocs-base.yml
            '');
          };

          docs-build = {
            type = "app";
            program = toString (pkgs.writeShellScript "docs-build" ''
              cd docs
              ${pkgs.mkdocs}/bin/mkdocs build -f mkdocs-base.yml
            '');
          };

          # Linting
          lint = {
            type = "app";
            program = toString (pkgs.writeShellScript "lint" ''
              echo "Running ruff..."
              ${pkgs.ruff}/bin/ruff check django_project
              echo "Running pre-commit..."
              ${pkgs.pre-commit}/bin/pre-commit run --all-files
            '');
          };

          # Formatting
          format = {
            type = "app";
            program = toString (pkgs.writeShellScript "format" ''
              echo "Formatting with ruff..."
              ${pkgs.ruff}/bin/ruff format django_project
              ${pkgs.ruff}/bin/ruff check --fix django_project
            '');
          };

          # Testing
          test = {
            type = "app";
            program = toString (pkgs.writeShellScript "test" ''
              cd django_project
              ${pythonEnv}/bin/python -m pytest
            '');
          };

          # Development server
          dev = {
            type = "app";
            program = toString (pkgs.writeShellScript "dev" ''
              echo "Starting development server..."
              make dev
            '');
          };

          # Package building
          build = {
            type = "app";
            program = toString (pkgs.writeShellScript "build" ''
              echo "Building Python package..."
              rm -rf dist/ build/ *.egg-info/
              ${pythonEnv}/bin/python -m build
              echo ""
              echo "Built packages:"
              ls -la dist/
            '');
          };

          build-wheel = {
            type = "app";
            program = toString (pkgs.writeShellScript "build-wheel" ''
              echo "Building wheel..."
              ${pythonEnv}/bin/python -m build --wheel
            '');
          };

          build-sdist = {
            type = "app";
            program = toString (pkgs.writeShellScript "build-sdist" ''
              echo "Building source distribution..."
              ${pythonEnv}/bin/python -m build --sdist
            '');
          };

          # Publishing
          publish = {
            type = "app";
            program = toString (pkgs.writeShellScript "publish" ''
              echo "Publishing to PyPI..."
              ${pythonEnv}/bin/python -m twine upload dist/*
            '');
          };

          publish-test = {
            type = "app";
            program = toString (pkgs.writeShellScript "publish-test" ''
              echo "Publishing to TestPyPI..."
              ${pythonEnv}/bin/python -m twine upload --repository testpypi dist/*
            '');
          };

          publish-check = {
            type = "app";
            program = toString (pkgs.writeShellScript "publish-check" ''
              echo "Checking packages..."
              ${pythonEnv}/bin/python -m twine check dist/*
            '');
          };

          # Versioning
          version = {
            type = "app";
            program = toString (pkgs.writeShellScript "version" ''
              cat django_project/version.txt
            '');
          };

          bump-patch = {
            type = "app";
            program = toString (pkgs.writeShellScript "bump-patch" ''
              ${pkgs.commitizen}/bin/cz bump --increment PATCH
            '');
          };

          bump-minor = {
            type = "app";
            program = toString (pkgs.writeShellScript "bump-minor" ''
              ${pkgs.commitizen}/bin/cz bump --increment MINOR
            '');
          };

          bump-major = {
            type = "app";
            program = toString (pkgs.writeShellScript "bump-major" ''
              ${pkgs.commitizen}/bin/cz bump --increment MAJOR
            '');
          };

          # Changelog
          changelog = {
            type = "app";
            program = toString (pkgs.writeShellScript "changelog" ''
              ${pkgs.git-cliff}/bin/git-cliff -o CHANGELOG.md
              echo "Changelog updated: CHANGELOG.md"
            '');
          };

          # Release
          release = {
            type = "app";
            program = toString (pkgs.writeShellScript "release" ''
              VERSION=$1
              if [ -z "$VERSION" ]; then
                echo "Usage: nix run .#release -- <version>"
                exit 1
              fi
              echo "Creating release $VERSION..."

              # Generate changelog
              ${pkgs.git-cliff}/bin/git-cliff -o CHANGELOG.md
              git add CHANGELOG.md
              git commit -m "chore: update changelog for $VERSION"

              # Tag
              git tag -a "v$VERSION" -m "Release $VERSION"

              # Build
              rm -rf dist/ build/ *.egg-info/
              ${pythonEnv}/bin/python -m build

              # Check
              ${pythonEnv}/bin/python -m twine check dist/*

              echo ""
              echo "Release $VERSION prepared!"
              echo "Next steps:"
              echo "  1. git push && git push --tags"
              echo "  2. nix run .#publish"
              echo "  3. gh release create v$VERSION dist/* --generate-notes"
            '');
          };

          release-github = {
            type = "app";
            program = toString (pkgs.writeShellScript "release-github" ''
              TAG=$(git describe --tags --abbrev=0)
              echo "Creating GitHub release for $TAG..."
              ${pkgs.gh}/bin/gh release create "$TAG" dist/* --generate-notes
            '');
          };

          # REUSE compliance check
          reuse-lint = {
            type = "app";
            program = toString (pkgs.writeShellScript "reuse-lint" ''
              ${pkgs.reuse}/bin/reuse lint
            '');
          };

          # Pre-commit
          pre-commit = {
            type = "app";
            program = toString (pkgs.writeShellScript "pre-commit" ''
              ${pkgs.pre-commit}/bin/pre-commit run --all-files
            '');
          };

          pre-commit-install = {
            type = "app";
            program = toString (pkgs.writeShellScript "pre-commit-install" ''
              ${pkgs.pre-commit}/bin/pre-commit install --install-hooks
            '');
          };
        };

        # Packages
        packages = {
          default = pkgs.python312Packages.buildPythonPackage {
            pname = "cloud-native-gis";
            version = "0.0.1";
            src = ./.;
            format = "pyproject";

            propagatedBuildInputs = with pkgs.python312Packages; [
              django
              djangorestframework
              django-cors-headers
              geopandas
              fiona
            ];
          };
        };
      }
    );
}
