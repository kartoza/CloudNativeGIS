-- SPDX-FileCopyrightText: 2024 Kartoza <info@kartoza.com>
-- SPDX-License-Identifier: AGPL-3.0-or-later
--
-- CloudNativeGIS Neovim Project Configuration
-- This file is automatically loaded by Neovim when working in this project.

local M = {}

-- =============================================================================
-- Project Settings
-- =============================================================================

-- Set Python path for Django
vim.env.PYTHONPATH = vim.fn.getcwd() .. "/django_project:" .. (vim.env.PYTHONPATH or "")
vim.env.DJANGO_SETTINGS_MODULE = "core.settings.dev"

-- =============================================================================
-- LSP Configuration
-- =============================================================================

-- Python LSP settings (pyright/basedpyright)
vim.g.cloudnativegis_pyright_settings = {
  python = {
    analysis = {
      autoSearchPaths = true,
      useLibraryCodeForTypes = true,
      diagnosticMode = "workspace",
      typeCheckingMode = "basic",
      extraPaths = { vim.fn.getcwd() .. "/django_project" },
    },
  },
}

-- Ruff LSP settings
vim.g.cloudnativegis_ruff_settings = {
  organizeImports = true,
  fixAll = true,
}

-- =============================================================================
-- DAP (Debug Adapter Protocol) Configuration
-- =============================================================================

local dap_ok, dap = pcall(require, "dap")
if dap_ok then
  -- Django debug configuration
  dap.configurations.python = dap.configurations.python or {}
  table.insert(dap.configurations.python, {
    type = "python",
    request = "launch",
    name = "Django: runserver",
    program = vim.fn.getcwd() .. "/django_project/manage.py",
    args = { "runserver", "--noreload" },
    django = true,
    justMyCode = false,
    env = {
      DJANGO_SETTINGS_MODULE = "core.settings.dev",
    },
  })

  table.insert(dap.configurations.python, {
    type = "python",
    request = "launch",
    name = "Django: test",
    program = vim.fn.getcwd() .. "/django_project/manage.py",
    args = { "test" },
    django = true,
    justMyCode = false,
    env = {
      DJANGO_SETTINGS_MODULE = "core.settings.test",
    },
  })

  table.insert(dap.configurations.python, {
    type = "python",
    request = "launch",
    name = "Pytest: current file",
    module = "pytest",
    args = function()
      return { vim.fn.expand("%:p"), "-v" }
    end,
    env = {
      DJANGO_SETTINGS_MODULE = "core.settings.test",
    },
  })
end

-- =============================================================================
-- Custom Commands
-- =============================================================================

-- Build package
vim.api.nvim_create_user_command("BuildPackage", function()
  vim.cmd("!just build")
end, { desc = "Build Python package (wheel + sdist)" })

-- Publish to PyPI
vim.api.nvim_create_user_command("PublishPyPI", function()
  vim.cmd("!just publish")
end, { desc = "Publish to PyPI" })

-- Publish to TestPyPI
vim.api.nvim_create_user_command("PublishTestPyPI", function()
  vim.cmd("!just publish-test")
end, { desc = "Publish to TestPyPI" })

-- Create GitHub release
vim.api.nvim_create_user_command("CreateRelease", function()
  vim.cmd("!just release-github")
end, { desc = "Create GitHub release" })

-- Version bumping
vim.api.nvim_create_user_command("BumpPatch", function()
  vim.cmd("!just bump-patch")
end, { desc = "Bump patch version" })

vim.api.nvim_create_user_command("BumpMinor", function()
  vim.cmd("!just bump-minor")
end, { desc = "Bump minor version" })

vim.api.nvim_create_user_command("BumpMajor", function()
  vim.cmd("!just bump-major")
end, { desc = "Bump major version" })

-- Generate changelog
vim.api.nvim_create_user_command("GenerateChangelog", function()
  vim.cmd("!just changelog")
end, { desc = "Generate CHANGELOG.md" })

-- Run tests
vim.api.nvim_create_user_command("RunTests", function(opts)
  local args = opts.args ~= "" and opts.args or ""
  vim.cmd("!just test " .. args)
end, { nargs = "?", desc = "Run pytest" })

-- Django manage.py
vim.api.nvim_create_user_command("DjangoManage", function(opts)
  vim.cmd("!cd django_project && python manage.py " .. opts.args)
end, { nargs = "+", desc = "Run Django manage.py command" })

-- =============================================================================
-- Statusline Integration
-- =============================================================================

-- Function to get current version (for statusline plugins)
function M.get_version()
  local version_file = vim.fn.getcwd() .. "/django_project/version.txt"
  if vim.fn.filereadable(version_file) == 1 then
    local version = vim.fn.readfile(version_file)[1]
    return "v" .. vim.fn.trim(version)
  end
  return ""
end

-- =============================================================================
-- Auto-formatting
-- =============================================================================

-- Format Python files on save with ruff
vim.api.nvim_create_autocmd("BufWritePre", {
  pattern = "*.py",
  callback = function()
    -- Only format if in this project
    if vim.fn.getcwd():match("CloudNativeGIS") then
      vim.lsp.buf.format({ async = false })
    end
  end,
  group = vim.api.nvim_create_augroup("CloudNativeGISFormat", { clear = true }),
})

-- =============================================================================
-- Telescope Integration
-- =============================================================================

local telescope_ok, telescope = pcall(require, "telescope.builtin")
if telescope_ok then
  -- Find Django files
  vim.api.nvim_create_user_command("FindDjangoFiles", function()
    telescope.find_files({
      cwd = vim.fn.getcwd() .. "/django_project",
      prompt_title = "Django Project Files",
    })
  end, { desc = "Find files in Django project" })

  -- Find tests
  vim.api.nvim_create_user_command("FindTests", function()
    telescope.find_files({
      cwd = vim.fn.getcwd() .. "/django_project",
      prompt_title = "Test Files",
      search_file = "test_*.py",
    })
  end, { desc = "Find test files" })

  -- Grep in Django project
  vim.api.nvim_create_user_command("GrepDjango", function()
    telescope.live_grep({
      cwd = vim.fn.getcwd() .. "/django_project",
      prompt_title = "Grep Django Project",
    })
  end, { desc = "Live grep in Django project" })
end

-- =============================================================================
-- Treesitter Configuration
-- =============================================================================

local ts_ok, ts_configs = pcall(require, "nvim-treesitter.configs")
if ts_ok then
  -- Ensure parsers are installed
  local ensure_installed = {
    "python",
    "javascript",
    "typescript",
    "tsx",
    "html",
    "css",
    "json",
    "yaml",
    "toml",
    "markdown",
    "markdown_inline",
    "sql",
    "nix",
    "lua",
    "vim",
    "vimdoc",
  }

  -- Note: This doesn't actually install, just sets the preference
  vim.g.cloudnativegis_treesitter_parsers = ensure_installed
end

-- =============================================================================
-- Project-specific snippets
-- =============================================================================

local luasnip_ok, ls = pcall(require, "luasnip")
if luasnip_ok then
  local s = ls.snippet
  local t = ls.text_node
  local i = ls.insert_node

  -- Django model snippet
  ls.add_snippets("python", {
    s("djmodel", {
      t({ "class " }),
      i(1, "ModelName"),
      t({ "(models.Model):", '    """' }),
      i(2, "Model description."),
      t({ '"""', "", "    " }),
      i(3, "field_name"),
      t(" = models."),
      i(4, "CharField"),
      t("("),
      i(5, "max_length=255"),
      t({ ")", "", "    def __str__(self):", "        return self." }),
      i(6, "field_name"),
      t({ "", "" }),
    }),

    -- Django serializer snippet
    s("djserializer", {
      t({ "class " }),
      i(1, "ModelName"),
      t({ "Serializer(serializers.ModelSerializer):", '    """Serializer for ' }),
      i(2, "ModelName"),
      t({ '."""', "", "    class Meta:", "        model = " }),
      i(3, "ModelName"),
      t({ "", '        fields = "__all__"', "" }),
    }),

    -- SPDX header snippet
    s("spdx", {
      t({
        "# SPDX-FileCopyrightText: 2024 Kartoza <info@kartoza.com>",
        "# SPDX-License-Identifier: AGPL-3.0-or-later",
        "",
      }),
    }),
  })
end

-- =============================================================================
-- Notify on load
-- =============================================================================

vim.defer_fn(function()
  local notify_ok, notify = pcall(require, "notify")
  if notify_ok then
    notify("CloudNativeGIS project loaded", "info", {
      title = "Project",
      timeout = 2000,
    })
  else
    print("CloudNativeGIS project configuration loaded")
  end
end, 100)

return M
