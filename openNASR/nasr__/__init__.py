from pandas import read_csv
from matplotlib import pyplot as plt

fd_in = '/home/aev/UCF Dropbox/Adan Vela/git-ucf/myNASRDB/app/data/csv/28DaySubscription_Effective_2023-11-02/'
f_ARB=fd_in+'ARB.csv'
ARB_DB = read_csv(f_ARB)