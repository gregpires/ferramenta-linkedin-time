import streamlit as st
from apify_client import ApifyClient
import pandas as pd
import io

# --- 1. Configurações da Página ---
st.set_page_config(page_title="Extrator LinkedIn (Privado)", page_icon="🔒")

# --- 2. TRAVA DE SEGURANÇA (Senha) ---
# O código para aqui se a senha estiver errada
with st.sidebar:
    st.header("🔒 Acesso Restrito")
    senha_digitada = st.text_input("Digite a senha do time:", type="password")

if senha_digitada != "Atlas@1234":
    st.warning("⚠️ Acesso negado. Por favor, insira a senha correta na barra lateral para utilizar a ferramenta.")
    st.stop()  # <--- Isso impede o resto do app de carregar

# --- 3. Interface Principal (Só carrega se a senha estiver certa) ---
st.title("💼 Extrator de Comentários LinkedIn")
st.markdown("""
Cole o link do post do LinkedIn abaixo. 
O sistema vai extrair os comentários e gerar um Excel formatado.
""")

# --- 4. Verificação de Token (Secrets) ---
if "APIFY_TOKEN" in st.secrets:
    api_token = st.secrets["APIFY_TOKEN"]
else:
    st.error("ERRO: O Token do Apify não foi configurado nos 'Secrets'.")
    st.stop()

actor_id = "datadoping/linkedin-post-comments-scraper"

# --- 5. Entrada de Dados ---
url_input = st.text_input("🔗 Link do Post do LinkedIn:", placeholder="https://www.linkedin.com/posts/...")

# --- 6. Botão e Lógica de Extração ---
if st.button("🚀 Extrair Dados", type="primary"):
    if not url_input:
        st.warning("Por favor, cole um link antes de processar.")
    else:
        status_text = st.empty()
        status_text.info("⏳ Conectando ao Apify... Aguarde.")
        
        try:
            # Conexão
            client = ApifyClient(api_token)
            
            # Configuração do Input (Lista de Posts)
            run_input = {
                "posts": [url_input], 
                "maxComments": 100,    
                "minDelay": 2,
                "maxDelay": 5
            }
            
            # Rodar o Ator
            run = client.actor(actor_id).call(run_input=run_input)
            
            status_text.info("⚙️ Processando e filtrando dados...")
            
            # Pegar os resultados
            dataset_items = client.dataset(run["defaultDatasetId"]).list_items().items
            
            if dataset_items:
                df = pd.DataFrame(dataset_items)

                # --- FILTRO DE COLUNAS ---
                colunas_desejadas = [
                    'text', 'posted_at', 'comment_url', 'author', 
                    'total_reactions', 'total_replies', 'owner_name', 
                    'owner_profile_url', 'input'
                ]
                
                # Garante que só pegamos colunas que existem para não dar erro
                colunas_finais = [col for col in colunas_desejadas if col in df.columns]
                df_filtrado = df[colunas_finais]
                
                # Criar Excel em memória
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df_filtrado.to_excel(writer, index=False, sheet_name='Dados')
                
                status_text.success(f"✅ Sucesso! {len(dataset_items)} comentários extraídos.")
                
                # Mostra prévia
                st.dataframe(df_filtrado.head())
                
                # Botão de Download
                st.download_button(
                    label="📥 Baixar Excel Filtrado",
                    data=buffer,
                    file_name="linkedin_comentarios.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                status_text.warning("O agente rodou, mas não encontrou comentários. Verifique se o post é público.")
                
        except Exception as e:
            status_text.error(f"Erro ao executar: {e}")

