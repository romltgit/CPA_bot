import logging

logfile = 'errors.log'
log = logging.getLogger("my_log")
log.setLevel(logging.ERROR)
FH = logging.FileHandler(logfile, encoding='utf-8')
basic_formater = logging.Formatter('%(asctime)s : [%(levelname)s] : %(message)s')
FH.setFormatter(basic_formater)
log.addHandler(FH)