-- Synthetic example.
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local announce = ReplicatedStorage.Remotes.Announce

-- LG004 and LG006: any client can broadcast any text to every player.
announce.OnServerEvent:Connect(function(player, message)
	announce:FireAllClients(message)
end)
