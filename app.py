import streamlit as st
from apify_client import ApifyClient
import pandas as pd
import io

# --- Configurações da Página ---
st.set_page_config(page_title="Extrator de LinkedIn", page_icon="💼")

# --- Título e Instruções ---
st.title("💼 Extrator de Comentários LinkedIn")
st.markdown("""
Cole o link do post do LinkedIn abaixo. 
O sistema vai acionar o agente no Apify, extrair os dados e gerar um Excel para você.
""")

# --- Entrada de Dados ---
# Tenta pegar o token dos segredos. Se não existir, avisa o usuário.
if "APIFY_TOKEN" in st.secrets:
    api_token = st.secrets["APIFY_TOKEN"]
else:
    st.error("ERRO: O Token do Apify não foi configurado nos 'Secrets' do Streamlit.")
    st.stop()

actor_id = "datadoping/linkedin-post-comments-scraper" # ID do ator correto

url_input = st.text_input("🔗 Link do Post do LinkedIn:", placeholder="https://www.linkedin.com/posts/...")

# --- Botão de Ação ---
if st.button("🚀 Extrair Dados", type="primary"):
    if not url_input:
        st.warning("Por favor, cole um link antes de processar.")
    else:
        status_text = st.empty()
        status_text.info("⏳ Conectando ao Apify e iniciando o agente... Aguarde.")
        
        try:
            # 1. Conexão
            client = ApifyClient(api_token)
            
            # 2. Configuração do Input (CORRIGIDO)
            # O erro anterior dizia que faltava o campo "posts". 
            # Esse ator exige uma lista de links dentro de "posts".
            run_input = {
                "posts": [url_input], 
                "maxComments": 100,    
                "minDelay": 2,
                "maxDelay": 5
            }
            
            # 3. Rodar o Ator (Modo Síncrono - Espera terminar)
            run = client.actor(actor_id).call(run_input=run_input)
            
            status_text.info("⚙️ Agente finalizou a extração. Baixando dados...")
            
            # 4. Pegar os resultados
            dataset_items = client.dataset(run["defaultDatasetId"]).list_items().items
            
            if dataset_items:
                # Converter para Tabela
                df = pd.DataFrame(dataset_items)
                
                # Criar Excel em memória
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='Dados')
                
                # Sucesso
                status_text.success(f"✅ Sucesso! {len(dataset_items)} itens extraídos.")
                
                # Mostra prévia
                st.dataframe(df.head())
                
                # Botão de Download
                st.download_button(
                    label="📥 Baixar Excel Completo",
                    data=buffer,
                    file_name="linkedin_dados.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                status_text.error("O agente rodou, mas não retornou dados. Verifique se o link é público e válido.")
                
        except Exception as e:
            status_text.error(f"Erro ao executar: {e}")

