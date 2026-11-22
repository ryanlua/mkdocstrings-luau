--[=[
	@class Greeter

	Builds greetings. Asynchronous results use [Promise].
]=]
local Greeter = {}

--[=[
	Greet someone by name.

	@external Promise https://eryn.io/roblox-lua-promise/api/Promise
	@param name string -- Who to greet
	@return Promise -- Resolves to the greeting
	@error "empty name" -- The name was blank
]=]
function Greeter.greet(name: string): Promise
	if name == "" then
		error("empty name")
	end
	return name
end

return Greeter
