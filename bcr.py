import bar_chart_race as bcr
import pandas as pd
df = pd.read_csv('dumpbcr.csv', index_col='date', parse_dates=['date'])

from_date = df.index[0].strftime("%Y-%m-%d")
to_date = df.index[-1].strftime("%Y-%m-%d")

bcr.bar_chart_race(
        fig_kwargs = {"figsize": (9, 5), "dpi": 150},
        df=df,
        filename='out.mp4',
        orientation='h',
        sort='desc',
        n_bars=30,
        fixed_max=True,
        title=f"Largest DN42 Networks ({from_date} to {to_date})",
#        bar_textposition='inside',
        bar_texttemplate=lambda x: f"{x**0.25:.2f}",
        tick_template=lambda x, _: f"{x**0.25:,.1f}",
        shared_fontdict={'family': 'Dejavu Sans Mono', 'weight': 'regular'},
)
