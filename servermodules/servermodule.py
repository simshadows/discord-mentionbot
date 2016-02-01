# Abstract Class (would've been an interface...)
# All server modules are subclasses of ServerModule.
class ServerModule:

	async def on_message(self, msg):
		raise NotImplementedError

	async def process_cmd(self, substr, msg):
		raise NotImplementedError






