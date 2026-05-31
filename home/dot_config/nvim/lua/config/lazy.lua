local lazypath = vim.fn.stdpath("data") .. "/lazy/lazy.nvim"
if not (vim.uv or vim.loop).fs_stat(lazypath) then
  local lazyrepo = "https://github.com/folke/lazy.nvim.git"
  local out = vim.fn.system({ "git", "clone", "--filter=blob:none", lazyrepo, lazypath })
  if vim.v.shell_error ~= 0 then
    vim.api.nvim_echo({
      { "Failed to clone lazy.nvim:\n", "ErrorMsg" },
      { out, "WarningMsg" },
      { "\nPress any key to exit..." },
    }, true, {})
    vim.fn.getchar()
    os.exit(1)
  end
end
vim.opt.rtp:prepend(lazypath)

-- LazyVim setup — options loaded first, then keymaps, then autocmds, then plugins
require("lazyvim.util").on_attach(function(keys, buf)
  -- Custom buffer-local keymaps can be set here
end)

-- Load config files in order: options → keymaps → autocmds → plugins
local config = vim.fn.stdpath("config") .. "/lua/config"
if vim.loop.fs_stat(config .. "/options.lua") then
  require("config.options")
end
if vim.loop.fs_stat(config .. "/keymaps.lua") then
  require("config.keymaps")
end
if vim.loop.fs_stat(config .. "/autocmds.lua") then
  require("config.autocmds")
end

-- Set up LazyVim and load plugins
local lazypath = vim.fn.stdpath("data") .. "/lazy/lazy.nvim"
if not (vim.uv or vim.loop).fs_stat(lazypath) then
  local lazyrepo = "https://github.com/folke/lazy.nvim.git"
  vim.fn.system({ "git", "clone", "--filter=blob:none", lazyrepo, lazypath })
end
vim.opt.rtp:prepend(lazypath)

require("lazy").setup({
  spec = {
    -- add LazyVim and import its plugins
    { "LazyVim/LazyVim", import = "lazyvim.plugins" },
    -- import/override with your plugins
    { import = "plugins" },
  },
  defaults = {
    lazy = false,
    version = false,
  },
  -- install = { missing = true },
  -- checker = {
  --   enabled = true,
  --   notify = false,
  -- },
  -- performance = {
  --   rtp = {
  --     disabled_plugins = {},
  --   },
  -- },
})
