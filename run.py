import multiprocessing as mp
import os, sys, re, time, copy
import configparser
import textwrap
import mentionbot.mentionbot as botentry

ini_file_name = "config.ini"

# These two regexes must both be used to verify a folder name.
re_dirname_fullmatch = re.compile("[a-z0-9_-]+") # This must be full-matched.
re_dirname_once = re.compile("[a-z0-9]") # There must be at least one match.

reconnect_on_error = None

bot_user_token = None

# TODO: Allow user customization of the cache directory's location.
config_defaults = {
	"DEFAULT": {
		"bot_user_token": "PLACEHOLDER",
		"bot_owner_id": "PLACEHOLDER",
	},
	"error_handling": {
		"kill_bot_on_message_exception": "FALSE",
		"reconnect_on_error": "TRUE",
		"message_bot_owner_on_error": "TRUE",
	},
	"api_keys": {
		"plotly_api_key": "PLACEHOLDER",
		"plotly_username": "PLACEHOLDER",
		"wolfram_alpha": "PLACEHOLDER",
	},
	"filenames": {
		"cache_folder": "cache",
	},
	"misc": {
		"default_command_prefix": "/",
		"message_bot_owner_on_init": "TRUE",
		"default_status": "bot is running",
		"initialization_status": "bot is initializing",
	},
}

# TODO: Consider merging this with the bot utils.py version.
accepted_true_strings  = {"true",  "yes", "y", "on",  "1", "set",   "ye" }
accepted_false_strings = {"false", "no",  "n", "off", "0", "clear", "clr"}

# Returns a dictionary object on a successful parse.
# Otherwise, returns None if no login key was found.
def ini_load():
	ret = None
	config = configparser.ConfigParser()
	if os.path.isfile(ini_file_name):
		# Parse the config file.
		config.read(ini_file_name)
		# Check if the login data is present.
		missing_login = False
		try:
			config["DEFAULT"]["bot_user_token"] # Attempt an access
		except KeyError as e:
			missing_login = True
		# Fill in default values.
		write_back = False
		for (k, v) in config_defaults.items():
			if k in config:
				section = config[k]
				for (k2, v2) in config_defaults[k].items():
					if not k2 in section:
						section[k2] = v2
						write_back = True
			else:
				config[k] = v
				write_back = True
		# Write back to the file if necessary.
		if write_back:
			with open(ini_file_name, "w") as f:
				config.write(f)
		
		if not missing_login:
			# Makes a deep copy, except with dictionaries.
			ret = {k: {k2: v2 for (k2, v2) in v.items()} for (k, v) in config.items()}
	else:
		# Set up a new file.
		config.read_dict(config_defaults)
		with open(ini_file_name, "w") as f:
			config.write(f)
	return ret

# Converts strings to bools, numbers, dates, etc, as necessary.
# Additionally, does validation by raising exceptio.
# Returns nothing, but raises an exception if an error is found.
def ini_parse(config_dict):
	
	must_be_bool = [
		("error_handling", "kill_bot_on_message_exception"),
		("error_handling", "reconnect_on_error"),
		("error_handling", "message_bot_owner_on_error"),
		("misc", "message_bot_owner_on_init"),
	]

	def convert_to_bool(key1, key2):
		assert isinstance(key1, str) and isinstance(key2, str)
		val = config_dict[key1][key2]
		assert isinstance(val, str)
		val = val.lower()
		if val in accepted_true_strings:
			val = True
		elif val in accepted_false_strings:
			val = False
		else:
			buf = "{} {} in {} must be 'TRUE' or 'FALSE'."
			raise ValueError(buf.format(key1, key2, ini_file_name))
		config_dict[key1][key2] = val
		return

	for (key1, key2) in must_be_bool:
		convert_to_bool(key1, key2)
		assert isinstance(config_dict[key1][key2], bool)

	# Check cache folder name.
	fname = config_dict["filenames"]["cache_folder"]
	if not re_dirname_once.search(fname):
		raise ValueError("Cache folder name must have at least one lowercase or digit.")
	if not re_dirname_fullmatch.fullmatch(fname):
		raise ValueError("Cache folder name must only be made of up lowercase, digits, underscores, or dashes.")
	return

def run():
	print("Reading config.ini settings...\n")
	config_dict = ini_load()
	if config_dict is None:
		buf = textwrap.dedent("""
			This appears to be your first time setting up this bot.

			Please edit the following items in in config.ini before relaunching:
				bot_user_token
				bot_owner_id

			Optionally, also fill in the other placeholders to enable further \
			functionality.
			""").strip()
		print(buf)
		return
	ini_parse(config_dict)

	reconnect_on_error = config_dict["error_handling"]["reconnect_on_error"]
	while True:
		config_dict_copy = copy.deepcopy(config_dict)
		proc = mp.Process(target=botentry.run, daemon=True, args=(config_dict_copy,))
		proc.start()
		proc.join()
		ret = proc.exitcode
		print("Bot terminated. Return value: " + str(ret))
		if ret == 0:
			print("Bot has completed execution.")
			return
		if not reconnect_on_error:
			print("reconnect_on_error is disabled.")
			print("Bot has completed execution.")
			return
		print("Abnormal exit. Reconnecting in 10 seconds.")
		time.sleep(10)
		print("Attempting to reconnect...")

if __name__ == '__main__':
   run()
