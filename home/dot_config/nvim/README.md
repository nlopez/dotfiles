# 💤 LazyVim

A personalized LazyVim configuration managed via [chezmoi](https://chezmoi.io/).

## Structure

```
nvim/
├── init.lua              # Bootstrap entry point
├── lua/
│   ├── config/           # LazyVim config overrides
│   │   ├── lazy.lua      # lazy.nvim setup + LazyVim import
│   │   ├── options.lua   # Neovim options
│   │   ├── keymaps.lua   # Neovim keybindings
│   │   ├── autocmds.lua  # Neovim autocommands
│   │   └── overrides.lua # LazyVim opts overrides
│   ├── mapping/          # Custom keybindings
│   └── plugins/          # Custom plugin specs
└── package.json          # Package metadata
```

## Adding Plugins

Edit `lua/plugins/init.lua` to add or override plugins:

```lua
return {
  -- Add your custom plugins here
  {
    "some-author/some-nvim-plugin",
    opts = {},
  },
}
```

## Overriding LazyVim Options

Edit `lua/config/overrides.lua`:

```lua
return {
  -- Override LazyVim options
  {
    "LazyVim/LazyVim",
    opts = {
      -- ...
    },
  },
}
```

## Managing Neovim Binary

- **macOS**: Installed via Homebrew (`brew install neovim`)
- **Linux**: Installed out-of-band (managed manually, not via chezmoi)
