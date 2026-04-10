import time
from orbs.log import log

start = time.time()
log.debug("test message")
end = time.time()

print("log write took:", end - start)