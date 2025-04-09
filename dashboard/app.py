import streamlit as st
import requests
from agentes.agente_recomendacao import AgenteRecomendacao

st.set_page_config(page_title="Sistema Multiagente - Predição de Evasão", layout="centered")

st.title("🔍 Sistema de Predição e Recomendação")
st.write("Insira a matrícula do aluno para obter predição e recomendações.")

matricula = st.text_input("Matrícula do Aluno")

if st.button("Consultar"):
    if not matricula:
        st.warning("Por favor, insira uma matrícula.")
    else:
        try:

            url_api = f"http://api_service:5000/predict_aluno/{matricula}"
            resposta = requests.get(url_api)
            resposta.raise_for_status()

            resultado = resposta.json()
            classe = resultado.get("previsao", "desconhecida")
            proba_evasao = resultado.get("proba_evadido ", 0.0)
            proba_formado = resultado.get("proba_formado ", 0.0)

            st.subheader("🎯 Predição")
            st.write(f"**Classe:** {classe}")
            st.write(f"**Probabilidade de Evasão:** {proba_evasao:.2f}%")
            st.write(f"**Probabilidade de Formar:** {proba_formado:.2f}%")

            agente_rec = AgenteRecomendacao()
            recomendacoes = agente_rec.recomendar(resultado)

            st.subheader("🧭 Recomendações")
            for rec in recomendacoes:
                st.markdown(f"- {rec}")

        except requests.exceptions.RequestException as e:
            st.error(f"Erro ao consultar a API: {e}")
        except Exception as e:
            st.error(f"Erro inesperado: {e}")