import streamlit as st
import requests
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="AI Data Analytics", layout="wide")

st.title("📊 AI Natural Language Analytics")
st.markdown("Chiedi al tuo file Parquet su S3 qualsiasi cosa in linguaggio naturale.")

# Configurazione API
API_URL = "https://55nizkyxef.execute-api.eu-south-1.amazonaws.com/default/natural-language-sql-engine"

# Sidebar per info
st.sidebar.header("Schema Dati")
st.sidebar.code("""
- Transaction_ID
- User_Name
- Age
- Country
- Product_Category
- Purchase_Amount
- Payment_Method
- Transaction_Date
""")

# Input utente
user_question = st.text_input("Inserisci la tua domanda (es: 'Quali sono i top 5 paesi per vendite?')")

if st.button("Analizza"):
    if user_question:
        with st.spinner("L'AI sta scrivendo il SQL ed interrogando S3..."):
            try:
                response = requests.post(API_URL, json={"question": user_question})
                
                if response.status_code == 200:
                    # Carichiamo la risposta
                    data = response.json()
                    
                    # Se la Lambda incapsula tutto in 'body' come stringa, lo decodifichiamo
                    if 'body' in data and isinstance(data['body'], str):
                        full_res = json.loads(data['body'])
                    else:
                        full_res = data

                    # Mappatura chiavi basata sul tuo output reale
                    sql_usato = full_res.get('generated_query')
                    risultati = full_res.get('result')

                    if sql_usato:
                        with st.expander("🔍 Vedi SQL generato"):
                            st.code(sql_usato, language="sql")

                    if risultati:
                        df = pd.DataFrame(risultati)
                        
                        col1, col2 = st.columns([1, 1])
                        
                        with col1:
                            st.subheader("Dati Estratti")
                            st.dataframe(df, use_container_width=True)
                        
                        with col2:
                            st.subheader("Visualizzazione")
                            # Se ci sono almeno 2 colonne, proviamo a fare un grafico
                            if len(df.columns) >= 2:
                                # Usiamo la prima colonna come X e la seconda come Y
                                fig = px.bar(df, x=df.columns[0], y=df.columns[1], 
                                             title=f"{df.columns[1]} per {df.columns[0]}",
                                             color=df.columns[0])
                                st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.warning("La query non ha prodotto risultati.")
                else:
                    st.error(f"Errore API: {response.status_code} - {response.text}")
            except Exception as e:
                st.error(f"Errore di connessione: {e}")
    else:
        st.warning("Inserisci una domanda.")