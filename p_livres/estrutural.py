import streamlit as st

from utils.estrutura.escada.escadas import show as show_escada

tabs = st.tabs(["Escada", "Reservatório", "Pilares", "Vigas", "Lajes", "Fundações"])

with tabs[0]:
    show_escada()
    