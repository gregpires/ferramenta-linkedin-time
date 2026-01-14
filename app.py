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
O sistema vai extrair os comentários e gerar um Excel com os campos selecionados.
""")

# --- Entrada de Dados ---
if "APIFY_TOKEN" in st.secrets:
    api_token = st.secrets["APIFY_TOKEN"]
else:
    st.error("ERRO: O Token do Apify não foi configurado nos 'Secrets'.")
    st.stop()

actor_id = "datadoping/linkedin-post-comments-scraper"

url_input = st.text_input("🔗 Link do Post do LinkedIn:", placeholder="https://www.linkedin.com/posts/...")

# --- Botão de Ação ---
if st.button("🚀 Extrair Dados", type="primary"):
    if not url_input:
        st.warning("Por favor, cole um link antes de processar.")
    else:
        status_text = st.empty()
        status_text.info("⏳ Conectando ao Apify... Aguarde.")
        
        try:
            # 1. Conexão
            client = ApifyClient(api_token)
            
            # 2. Configuração do Input
            run_input = {
                "posts": [url_input], 
                "maxComments": 100,    
                "minDelay": 2,
                "maxDelay": 5
            }
            
            # 3. Rodar o Ator
            run = client.actor(actor_id).call(run_input=run_input)
            
            status_text.info("⚙️ Processando dados...")
            
            # 4. Pegar os resultados
            dataset_items = client.dataset(run["defaultDatasetId"]).list_items().items
            
            if dataset_items:
                df = pd.DataFrame(dataset_items)

                # --- FILTRO DE COLUNAS (NOVO) ---
                # Lista exata que você pediu
                colunas_desejadas = [
                    'text', 'posted_at', 'comment_url', 'author', 
                    'total_reactions', 'total_replies', 'owner_name', 
                    'owner_profile_url', 'input'
                ]
                
                # Seleciona apenas as colunas que realmente vieram no resultado para evitar erro
                colunas_finais = [col for col in colunas_desejadas if col in df.columns]
                df_filtrado = df[colunas_finais]
                
                # Criar Excel em memória com o DF filtrado
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df_filtrado.to_excel(writer, index=False, sheet_name='Dados')
                
                status_text.success(f"✅ Sucesso! {len(dataset_items)} comentários extraídos.")
                
                # Mostra prévia filtrada
                st.dataframe(df_filtrado.head())
                
                st.download_button(
                    label="📥 Baixar Excel Filtrado",
                    data=buffer,
                    file_name="linkedin_comentarios.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                status_text.warning("O agente rodou, mas não encontrou comentários ou dados.")
                
        except Exception as e:
            status_text.error(f"Erro ao executar: {e}")

