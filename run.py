import multiprocessing as mp
import os, sys, time
import mentionbot.mentionbot as botentry

RECONNECT_ON_ERROR = True

def run():
	while True:
		proc = mp.Process(target=botentry.run, daemon=True)
		proc.start()
		proc.join()
		ret = proc.exitcode
		print("Bot terminated. Return value: " + str(ret))
		if ret == 0:
			print("Bot has completed execution.")
			return
		if not RECONNECT_ON_ERROR:
			print("RECONNECT_ON_ERROR is disabled.")
			print("Bot has completed execution.")
			return
		print("Abnormal exit. Reconnecting in 10 seconds.")
		time.sleep(10)
		print("Attempting to reconnect...")

if __name__ == '__main__':
   run()
