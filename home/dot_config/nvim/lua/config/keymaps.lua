-- Keymaps are loaded after options and before autocmds
-- Default keymaps: https://github.com/LazyVim/LazyVim/blob/main/lua/lazyvim/config/keymaps.lua
-- Add any additional keymaps here

local map = vim.keymap.set

-- ── General ───────────────────────────────────────────────────────────

-- Use k/l to go to left/right file in a split
map({ "n", "x", "o" }, "<C-h>", "<C-w>h", { desc = "Switch to Left Window" })
map({ "n", "x", "o" }, "<C-j>", "<C-w>j", { desc = "Switch to Below Window" })
map({ "n", "x", "o" }, "<C-k>", "<C-w>k", { desc = "Switch to Above Window" })
map({ "n", "x", "o" }, "<C-l>", "<C-w>l", { desc = "Switch to Right Window" })

-- Resize with Alt+ arrows
map("n", "<M-Left>", "<cmd>resize -2<CR>", { desc = "Resize Left" })
map("n", "<M-Right>", "<cmd>resize +2<CR>", { desc = "Resize Right" })
map("n", "<M-Up>", "<cmd>resize -2<CR>", { desc = "Resize Up" })
map("n", "<M-Down>", "<cmd>resize +2<CR>", { desc = "Resize Down" })
