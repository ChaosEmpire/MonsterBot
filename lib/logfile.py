import logging

# Logging
def log(msg,filename):
        print (msg)
        logging.basicConfig(filename="log/" + filename + ".log", format="%(asctime)s|%(message)s", level=logging.INFO)
        logging.info(msg)

