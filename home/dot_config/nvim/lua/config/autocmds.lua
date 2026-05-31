-- Autocommands are loaded after keymaps
-- Default autocmds: https://github.com/LazyVim/LazyVim/blob/main/lua/lazyvim/config/autocmds.lua
-- Add any additional autocmds here

local autocmd = vim.api.nvim_create_autocmd
local cmd = vim.api.nvim_create_user_command

-- ── Highlight on yank ─────────────────────────────────────────────────
autocmd("TextYankPost", {
  callback = function()
    vim.highlight.on_yank()
  end,
  group = vim.api.nvim_create_augroup("lazyvim_yank_highlight", { clear = true }),
})

-- ── Auto-create dir when saving a file ────────────────────────────────
autocmd("BufWritePre", {
  pattern = "*",
  command = "call mkdir(fnamemodify(expand('%:p'), ':h'), 'p')",
})
