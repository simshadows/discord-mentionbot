import multiprocessing as mp
import os, sys, time
import mentionbot.mentionbot as botentry

def run():
	proc = mp.Process(target=botentry.run, daemon=True)
	proc.start()
	proc.join()
	ret = proc.exitcode
	print("Bot terminated. Return value:")
	print(str(ret))

if __name__ == '__main__':
   run()
