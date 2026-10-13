-- Synthetic example. Every handler in the vulnerable folder is intentionally unsafe.
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local giveCoins = ReplicatedStorage.Remotes.GiveCoins
local spawnParts = ReplicatedStorage.Remotes.SpawnParts

-- LG003 and LG004: the client decides how many coins it gets.
giveCoins.OnServerEvent:Connect(function(player, amount)
	local stats = player.leaderstats
	stats.Coins.Value += amount
end)

-- LG004 and LG008: the client decides how many parts the server creates.
spawnParts.OnServerEvent:Connect(function(player, count)
	for i = 1, count do
		Instance.new("Part").Parent = workspace
	end
end)
