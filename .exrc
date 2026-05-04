" SPDX-FileCopyrightText: 2024 Kartoza <info@kartoza.com>
" SPDX-License-Identifier: AGPL-3.0-or-later
"
" CloudNativeGIS Neovim Project Configuration
" WhichKey shortcuts under <leader>p (Project)
"
" This file is sourced automatically by Neovim when working in this project.
" Requires: which-key.nvim

" Ensure we only load this once
if exists('g:cloudnativegis_loaded')
  finish
endif
let g:cloudnativegis_loaded = 1

" Set Python path for Django
let $PYTHONPATH = getcwd() . '/django_project:' . $PYTHONPATH

" =============================================================================
" WhichKey Mappings (requires which-key.nvim)
" =============================================================================

lua << EOF
local ok, wk = pcall(require, "which-key")
if not ok then
  return
end

wk.add({
  { "<leader>p", group = "Project (CloudNativeGIS)" },

  -- Development
  { "<leader>pd", group = "Documentation" },
  { "<leader>pds", "<cmd>!just docs<cr>", desc = "Serve docs" },
  { "<leader>pdb", "<cmd>!just docs-build<cr>", desc = "Build docs" },

  { "<leader>pf", "<cmd>!just format<cr>", desc = "Format code" },
  { "<leader>pl", "<cmd>!just lint<cr>", desc = "Lint code" },
  { "<leader>pt", "<cmd>!just test<cr>", desc = "Run tests" },
  { "<leader>pr", "<cmd>!just dev<cr>", desc = "Run dev server" },
  { "<leader>pc", "<cmd>!just check<cr>", desc = "Pre-commit check" },

  -- Docker
  { "<leader>pD", group = "Docker" },
  { "<leader>pDu", "<cmd>!just up<cr>", desc = "Docker up" },
  { "<leader>pDd", "<cmd>!just down<cr>", desc = "Docker down" },
  { "<leader>pDb", "<cmd>!just docker-build<cr>", desc = "Docker build" },

  -- Git
  { "<leader>pg", group = "Git" },
  { "<leader>pgs", "<cmd>!git status<cr>", desc = "Git status" },
  { "<leader>pgp", "<cmd>!git push<cr>", desc = "Git push" },
  { "<leader>pgl", "<cmd>!git log --oneline -20<cr>", desc = "Git log" },

  -- Release & Publishing
  { "<leader>pR", group = "Release" },
  { "<leader>pRb", "<cmd>!just build<cr>", desc = "Build package" },
  { "<leader>pRp", "<cmd>!just publish<cr>", desc = "Publish to PyPI" },
  { "<leader>pRt", "<cmd>!just publish-test<cr>", desc = "Publish to TestPyPI" },
  { "<leader>pRc", "<cmd>!just publish-check<cr>", desc = "Check package" },
  { "<leader>pRv", "<cmd>!just version<cr>", desc = "Show version" },
  { "<leader>pRg", "<cmd>!just release-github<cr>", desc = "GitHub release" },
  { "<leader>pRC", "<cmd>!just changelog<cr>", desc = "Generate changelog" },

  -- Version bumping
  { "<leader>pV", group = "Version" },
  { "<leader>pVp", "<cmd>!just bump-patch<cr>", desc = "Bump patch" },
  { "<leader>pVm", "<cmd>!just bump-minor<cr>", desc = "Bump minor" },
  { "<leader>pVM", "<cmd>!just bump-major<cr>", desc = "Bump major" },

  -- Compliance
  { "<leader>pC", group = "Compliance" },
  { "<leader>pCr", "<cmd>!reuse lint<cr>", desc = "REUSE lint" },

  -- Quick actions
  { "<leader>pm", "<cmd>make<cr>", desc = "Make (default)" },
  { "<leader>pi", "<cmd>!pre-commit install<cr>", desc = "Install pre-commit" },
})
EOF
