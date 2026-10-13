-- Synthetic example.
local pad = workspace.Pad

-- LG010: Touched fires repeatedly, so this damages many times per touch.
pad.Touched:Connect(function(hit)
	local humanoid = hit.Parent:FindFirstChild("Humanoid")
	if humanoid then
		humanoid:TakeDamage(10)
	end
end)
