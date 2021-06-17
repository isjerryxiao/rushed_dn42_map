import bar_chart_race as bcr
import pandas as pd
df = pd.read_csv('dumpbcr.csv', index_col='date', parse_dates=['date'])

bcr.bar_chart_race(
        df=df,
        filename='test.mp4',
        orientation='h',
        sort='desc',
        n_bars=8,
)
