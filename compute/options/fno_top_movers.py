import pandas as pd

def get_top_movers(snapshot):
    df = pd.DataFrame(snapshot)
    df["change_pct"] = df["change_pct"].astype(float)

    gainers = df.sort_values("change_pct", ascending=False).head(5)
    losers = df.sort_values("change_pct").head(5)

    return gainers, losers
