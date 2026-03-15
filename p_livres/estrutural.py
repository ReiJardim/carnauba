import streamlit as st

from utils.estrutura.escada.escadas import show as show_escada

tab_escada , tab_estrutura = st.tabs(["Escada", "Reservatório", "Pilares", "Vigas", "Lajes", "Fundações"])

with tab_escada:
    show_escada()
    