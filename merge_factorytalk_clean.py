# 🧩 Merge FactoryTalk CSVs (raw + clean tag names, no scaling, auto-download)
import pandas as pd
from google.colab import files
import re

print("📂 Upload historian CSVs (TT-01, Motors, Flow, WF optional)")
uploaded = files.upload()

def clean_name(full):
    full = str(full)
    tag = re.split(r"[./]", full)[-1]
    return tag.strip()

def clean_csv(path):
    df = pd.read_csv(path, encoding="utf-16", on_bad_lines="skip")
    df.columns = [c.strip().title() for c in df.columns]
    df = df[[c for c in ['Time','Name','Value','Quality'] if c in df.columns]].copy()
    df['Time']  = pd.to_datetime(df['Time'], errors='coerce')
    df['Value'] = pd.to_numeric(df['Value'], errors='coerce')
    df['Tag']   = df['Name'].apply(clean_name)
    df.dropna(subset=['Time','Value'], inplace=True)
    return df

frames = [clean_csv(fn) for fn in uploaded.keys()]
combined = pd.concat(frames, ignore_index=True)
combined.sort_values('Time', inplace=True)
combined.reset_index(drop=True, inplace=True)

out_name = 'Last_30_Day_Data_Group_45.csv'
combined.to_csv(out_name, index=False)
files.download(out_name)

print(f"✅ Done: {len(combined):,} rows → {out_name}")
print('📊 Columns: Time | Name | Value | Quality | Tag')
