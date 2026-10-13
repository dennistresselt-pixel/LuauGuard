-- Synthetic example.
local modules = script.Parent.Modules

-- LG002: a variable chooses which module runs.
local function load(name)
	return require(modules[name])
end

-- LG001: dynamic code execution.
local fn = loadstring("return 1 + 1")
print(load("Util"), fn)
