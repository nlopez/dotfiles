hl.config({
    general = {
        layout = "scrolling",
    },
    dwindle = {
        preserve_split = true,
    },
    scrolling = {
        fullscreen_on_one_column = true,
        column_width = 0.5,
        focus_fit_method = 1, -- 0 = center focused column, 1 = fit
        follow_focus = true,
        explicit_column_widths = "0.333, 0.5, 0.667, 1.0",
        direction = "right",
    },
    ecosystem = {
        no_update_news = true,
        no_donation_nag = true,
    },
    misc = {
        col = {
            splash = CACHYLGREEN,
        },
        middle_click_paste = false,
        enable_swallow = true,
        swallow_regex = "(kitty|ghostty|[Kk]onsole|Alacritty|gnome-terminal|xfce[0-9]?-terminal)",
        vrr = 3,
    },
    render = {
        direct_scanout = 2,
    },
    xwayland = {
        force_zero_scaling = true
    },
})
