-- Synthetic example.
local Players = game:GetService("Players")
local player = Players.LocalPlayer

-- LG005: the client edits its own currency.
player.leaderstats.Coins.Value += 100
