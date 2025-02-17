import streamlit as st
import pandas as pd
from datetime import timedelta
from common import tcx_to_df, get_tcx_data, get_zone, Colors

st.title("Comparing Workouts")

uploaded_files = st.file_uploader("Choose two TCX files", type=["tcx"], accept_multiple_files=True)
ftp = st.number_input("Functional Threshold Power (FTP)", 0, 1000, 200)

st.divider()

if uploaded_files:
    dfs = []
    zone_counts_dfs = []
    for file in uploaded_files:
        filename = file.name.split('.')[0]
        tcx_data = get_tcx_data(file)
        df = tcx_to_df(tcx_data, kph=True)
        df["zone"] = df["power"].apply(lambda x: get_zone(x, ftp))
        dfs.append(df)
        zone_counts = round(df["zone"].value_counts(normalize=True).sort_index() * 100, 1)
        zone_durations = [str(timedelta(seconds=zone_count)) for zone_count in df["zone"].value_counts().sort_index()]
        zone_counts_df = pd.DataFrame(
            {
                "Zone": zone_counts.index + 1,
                f"Percent-{filename}": zone_counts.values,
                f"Duration-{filename}": zone_durations,
            }
        )
        zone_counts_df.set_index("Zone", inplace=True)
        zone_counts_dfs.append(zone_counts_df)
    
    # merge zone_conts_dfs
    merged_zone_counts_df = pd.concat(zone_counts_dfs, axis=1)

    # Highlight the max duration for each zone
    def highlight_max_duration(row):
        max_duration = max(row.filter(like="Duration-"))
        return [f'background-color: {Colors.YELLOW}; color: black' if v == max_duration else '' for v in row]

    styled_df = merged_zone_counts_df.style.apply(highlight_max_duration, axis=1)
    st.dataframe(styled_df)
    Y = [f"Percent-{file.name.split('.')[0]}" for file in uploaded_files]
    Y_label = [file.name.split('.')[0] for file in uploaded_files]
    st.bar_chart(merged_zone_counts_df, y=Y, y_label=Y_label, use_container_width=True, horizontal=True, stack=False)
