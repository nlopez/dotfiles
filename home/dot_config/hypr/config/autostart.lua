-- Auto-start config
-- if you dont use UWSM add your auto start programs here, otherwise use XDG autostart https://wiki.archlinux.org/title/XDG_Autostart

hl.on("hyprland.start", function ()
    -- Not needed with UWSM:
    --   env propagation -> uwsm prepare-env / finalize
    --   hl.exec_cmd("dbus-update-activation-environment --systemd --all")
    --   noctalia        -> ~/.config/autostart/dev.noctalia.Noctalia.desktop
    hl.exec_cmd("xhost +SI:localuser:root")
end)
