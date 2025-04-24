
import time
import pandas as pd
import csv
import logging
# Setting: logging style
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s.%(msecs)03d [%(levelname)s] %(message)s ",
    datefmt="%Y-%m-%d %H:%M:%S",
    )
path = "./QAPokerMockClient/accounts.csv"

with open(path, 'r') as file:
    csvReader = csv.reader(file)
    listReport = list(csvReader)
print(listReport)
for i,v in enumerate(listReport):
    if i == 10:
        break
    print(i)
    print(v)
