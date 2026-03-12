import streamlit as st
import requests
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="AI Data Analytics", layout="wide")

st.title("AI Natural Language Analytics")
st.markdown("Ask an analytics question in natural language.")

# Configurazione API
API_URL = "https://55nizkyxef.execute-api.eu-south-1.amazonaws.com/default/natural-language-sql-engine"

# Sidebar per info
st.sidebar.header("Data Scheme")
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

# User input 
user_question = st.text_input("Write your question (e.g. 'Which are the top 5 countries by purchases?')")

if st.button("Analyzing"):
    if user_question:
        with st.spinner("AI is writing SQL and queering S3..."):
            try:
                response = requests.post(API_URL, json={"question": user_question})
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # decoding lambda body
                    if 'body' in data and isinstance(data['body'], str):
                        full_res = json.loads(data['body'])
                    else:
                        full_res = data

                    sql_usato = full_res.get('generated_query')
                    risultati = full_res.get('result')

                    if sql_usato:
                        with st.expander("See generated SQL"):
                            st.code(sql_usato, language="sql")

                    if risultati:
                        df = pd.DataFrame(risultati)
                        
                        col1, col2 = st.columns([1, 1])
                        
                        with col1:
                            st.subheader("Extracted data")
                            st.dataframe(df, use_container_width=True)
                        
                        with col2:
                            st.subheader("View")
                            # Se ci sono almeno 2 colonne, proviamo a fare un grafico
                            if len(df.columns) >= 2:
                                # Usiamo la prima colonna come X e la seconda come Y
                                fig = px.bar(df, x=df.columns[0], y=df.columns[1], 
                                             title=f"{df.columns[1]} per {df.columns[0]}",
                                             color=df.columns[0])
                                st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.warning("Query didn't produced any result.")
                else:
                    st.error(f"API Error: {response.status_code} - {response.text}")
            except Exception as e:
                st.error(f"Connection error: {e}")
    else:
        st.warning("Insert a question.")