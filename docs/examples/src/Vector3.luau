--[=[
	@class Vector3
	@tag math
	@since v1.0.0

	A three-component vector.

	Create one with [Vector3.new]. Scale it through [Options].
]=]
local Vector3 = {}
Vector3.__index = Vector3

--[=[
	The X component.

	@prop X number
	@within Vector3
	@readonly
]=]
Vector3.X = 0

--[=[
	The Y component. Hidden unless private members are shown.

	@prop Y number
	@within Vector3
	@private
]=]
Vector3.Y = 0

--[=[
	Homogeneous coordinate. Not part of the stable API yet.

	@prop W number
	@within Vector3
	@unreleased
]=]
Vector3.W = 0

--[=[
	Create a vector from components.

	@param x number -- X component
	@param y number -- Y component
	@param z? number -- Optional Z, defaults to 0
	@return Vector3 -- The new vector
	@error "invalid component" -- A component was not a number
]=]
function Vector3.new(x: number, y: number, z: number?): Vector3
	if type(x) ~= "number" or type(y) ~= "number" or (z ~= nil and type(z) ~= "number") then
		error("invalid component")
	end
	local self = setmetatable({
		X = x,
		Y = y,
		Z = z or 0,
	}, Vector3)
	return self
end

--[=[
	Dot product with another vector.

	See [Vector3.new] for construction.

	@param other Vector3 -- The other vector
	@return number -- The dot product
	@yields
	@server
	@client
]=]
function Vector3:dot(other: Vector3): number
	return self.X * other.X + self.Y * other.Y + (self.Z or 0) * (other.Z or 0)
end

--[=[
	Length of the vector.

	@deprecated v2.0.0 -- Use a dedicated length helper instead.
	@return number -- The magnitude
]=]
function Vector3:magnitude(): number
	return math.sqrt(self:dot(self))
end

--[=[
	Internal helper excluded from the public docs.

	@ignore
]=]
function Vector3:_secret(): nil
	return nil
end

--[=[
	A vector constrained to unit length.

	@type UnitVector { number }
	@within Vector3
]=]

--[=[
	@interface Options
	@within Vector3
	@since v1.1.0

	.Scale number -- Uniform scale applied after creation
	.Unit boolean -- Return a [UnitVector] instead

	Options accepted by constructors.
]=]

return Vector3
