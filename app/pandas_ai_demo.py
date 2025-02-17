import os

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
from pandasai import SmartDataframe
from pandasai.llm.local_llm import LocalLLM

st.title("pandas-ai streamlit interface")

st.write("A demo interface for [PandasAI](https://github.com/gventuri/pandas-ai)")
st.write("Looking for an example *.csv-file?, check [here](https://gist.github.com/netj/8836201) (Download ZIP).")

llm = LocalLLM(api_base="http://localhost:11434/v1", model="llama3.2:latest")

st.session_state.prompt_history = []
st.session_state.df = None

if st.session_state.df is None:
    uploaded_file = st.file_uploader(
        "Choose a CSV file. This should be in long format (one datapoint per row).",
        type="csv",
    )
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        st.session_state.df = df

with st.form("Question"):
    question = st.text_input("Question", value="", type="default")
    submitted = st.form_submit_button("Submit")
    if submitted:
        with st.spinner():
            smart_df = SmartDataframe(st.session_state.df, config={"llm": llm})
            x = smart_df.chat(question)
            if os.path.isfile("temp_chart.png"):
                im = plt.imread("temp_chart.png")
                st.image(im)
                os.remove("temp_chart.png")

            if x is not None:
                st.write(x)
            st.session_state.prompt_history.append(question)

if st.session_state.df is not None:
    st.subheader("Current dataframe:")
    st.write(st.session_state.df)

st.subheader("Prompt history:")
st.write(st.session_state.prompt_history)


if st.button("Clear"):
    st.session_state.prompt_history = []
    st.session_state.df = None
