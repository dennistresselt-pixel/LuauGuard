-- Synthetic example.
local HttpService = game:GetService("HttpService")
local ReplicatedStorage = game:GetService("ReplicatedStorage")

local search = ReplicatedStorage.Remotes.Search

-- LG009 and LG011: the client controls part of an outbound request.
search.OnServerInvoke = function(player, query)
	return HttpService:GetAsync("https://example.com/search?q=" .. query)
end
