-- Options are automatically loaded before lazy.nvim startup
-- Default options that are always set:
-- https://github.com/LazyVim/LazyVim/blob/main/lua/lazyvim/config/options.lua
-- Add any additional options here

local opt = vim.opt

-- ── General ───────────────────────────────────────────────────────────
opt.clipboard = "unnamedplus"
opt.cursorline = true
opt.hidden = true
opt.history = 1000
opt.termguicolors = true

-- ── Searching ─────────────────────────────────────────────────────────
opt.ignorecase = true
opt.smartcase = true

-- ── Indent ────────────────────────────────────────────────────────────
opt.expandtab = true
opt.shiftwidth = 2
opt.tabstop = 2
opt.smartindent = true
opt.autoindent = true
opt.breakindent = true

-- ── Line numbers ──────────────────────────────────────────────────────
opt.number = true
opt.relativenumber = true

-- ── Scrolling ─────────────────────────────────────────────────────────
opt.scrolloff = 8
opt.sidescrolloff = 8

-- ── Split windows ─────────────────────────────────────────────────────
opt.splitbelow = true
opt.splitright = true

-- ── File encoding ─────────────────────────────────────────────────────
opt.encoding = "utf-8"

-- ── Mouse ─────────────────────────────────────────────────────────────
opt.mouse = "a"

-- ── Timeout ───────────────────────────────────────────────────────────
opt.timeoutlen = 300
opt.ttimeoutlen = 10

-- ── Undo ──────────────────────────────────────────────────────────────
opt.undofile = true

-- ── Diagnostics ───────────────────────────────────────────────────────
opt.signcolumn = "yes"
