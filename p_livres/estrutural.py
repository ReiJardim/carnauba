import streamlit as st

from utils.estrutura.escada.escadas import show as show_escada
from utils.estrutura.reservatorio.reservatorio import show as show_reservatorio

tabs = st.tabs(["Escada", "Reservatório", "Pilares", "Vigas", "Lajes", "Fundações"])

with tabs[0]:
    show_escada()

with tabs[1]:
    show_reservatorio()

    