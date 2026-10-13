-- Synthetic example of the same features written defensively.
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local buyRemote = ReplicatedStorage.Remotes.BuyItem
local spawnRemote = ReplicatedStorage.Remotes.SpawnParts

local PRICES = { Sword = 100, Shield = 150 }
local lastBuy = {}

buyRemote.OnServerEvent:Connect(function(player, itemName)
	if typeof(itemName) ~= "string" or PRICES[itemName] == nil then
		return
	end
	if os.clock() - (lastBuy[player.UserId] or 0) < 1 then
		return
	end
	lastBuy[player.UserId] = os.clock()

	local price = PRICES[itemName]
	local coins = player.leaderstats.Coins
	if coins.Value < price then
		return
	end
	coins.Value -= price
end)

spawnRemote.OnServerEvent:Connect(function(player, count)
	if typeof(count) ~= "number" then
		return
	end
	count = math.clamp(math.floor(count), 1, 10)
	for i = 1, count do
		Instance.new("Part").Parent = workspace
	end
end)
