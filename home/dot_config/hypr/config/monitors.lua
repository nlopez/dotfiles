-- Monitor wiki https://wiki.hypr.land/Configuring/Basics/Monitors/

hl.monitor({ output = MONITOR1, mode = "highrr", vrr = 0, scale = 1.25, position = "0x0",    bitdepth = 10 })
hl.monitor({ output = MONITOR2, mode = "highrr", vrr = 3, scale = 1.25, position = "2048x0", bitdepth = 10 })
hl.monitor({ output = MONITOR3, mode = "highrr", vrr = 0, scale = 1.25, position = "4800x0", bitdepth = 10 })
