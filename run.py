import multiprocessing as mp
import os, sys, time, copy
import configparser
import textwrap
import mentionbot.mentionbot as botentry

ini_file_name = "config.ini"

reconnect_on_error = None

bot_user_token = None

config_defaults = {
	"DEFAULT": {
		"bot_user_token": "PLACEHOLDER",
	},
	"error_handling": {
		"kill_bot_on_message_exception": "FALSE",
		"reconnect_on_error": "TRUE",
	},
	"api_keys": {
		"plotly_api_key": "PLACEHOLDER",
		"plotly_username": "PLACEHOLDER",
		"wolfram_alpha": "PLACEHOLDER",
	}
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
	return

def run():
	print("Reading config.ini settings...")
	config_dict = ini_load()
	if config_dict is None:
		buf = "Please edit bot_user_token in config.ini with your bot login,"
		buf += " then relaunch."
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
