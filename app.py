import streamlit as st
from apify_client import ApifyClient
import pandas as pd
import io
import time
import requests
from datetime import datetime

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(page_title="Atlas System", page_icon="🔒", layout="centered")

# --- 2. ATORES (ROBÔS) ---
ACTOR_COMMENTS = "datadoping/linkedin-post-comments-scraper"
ACTOR_LIKES = "harvestapi/linkedin-post-reactions"

# --- 3. CSS VISUAL ---
st.markdown("""
<style>
    .stApp { background-color: #1E1E1E; color: white; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    .login-container {
        background-color: #2D2D2D;
        padding: 40px;
        border-radius: 15px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.5);
        border: 1px solid #444;
        text-align: center;
        margin-top: 50px;
    }
    .stTextInput > div > div > input { background-color: #404040; color: white; border: 1px solid #555; }
    h1 { color: #FF4B4B !important; }
    .stMetric { background-color: #333; padding: 10px; border-radius: 5px; }
</style>
""", unsafe_allow_html=True)

# --- 4. SESSÃO ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

# --- 5. TELA DE LOGIN (APENAS SENHA) ---
def login_screen():
    # Verifica se a senha mestre existe nos Secrets
    if "SENHA_ACESSO" not in st.secrets:
        st.error("⚠️ Configure a SENHA_ACESSO nos Secrets do Streamlit!")
        st.stop()

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        st.title("🔒 ATLAS SYSTEM")
        st.markdown("Acesso Restrito")
        
        # Campo único de senha
        senha = st.text_input("Digite a Senha", type="password")
        
        if st.button("ACESSAR", type="primary"):
            # Compara direto com o segredo
            if senha == st.secrets["SENHA_ACESSO"]:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Senha incorreta.")
        st.markdown('</div>', unsafe_allow_html=True)

# --- 6. APP PRINCIPAL ---
def main_app():
    col_logout = st.columns([6, 1])
    with col_logout[1]:
        if st.button("Sair"):
            st.session_state.authenticated = False
            st.rerun()

    st.title("🚀 Extrator Full LinkedIn")
    st.markdown("Extração de **Comentários + Likes** com envio para Clay.")
    
    if "APIFY_TOKEN" not in st.secrets:
        st.error("Token Apify não configurado.")
        st.stop()
        
    api_token = st.secrets["APIFY_TOKEN"]
    clay_url = st.secrets.get("CLAY_WEBHOOK", "") 

    url_input = st.text_input("Link do Post:", placeholder="https://www.linkedin.com/posts/...")
    
    if st.button("Iniciar Extração Completa", type="primary"):
        if not url_input:
            st.warning("Cole o link.")
        else:
            with st.status("🔍 Processando...", expanded=True) as status:
                try:
                    client = ApifyClient(api_token)
                    
                    # 1. COMENTÁRIOS
                    status.write("💬 Extraindo Comentários...")
                    run_comments = client.actor(ACTOR_COMMENTS).call(run_input={ 
                        "posts": [url_input], "maxComments": 200, "minDelay": 1, "maxDelay": 4 
                    })
                    data_comments = client.dataset(run_comments["defaultDatasetId"]).list_items().items
                    df_comments = pd.DataFrame(data_comments)
                    
                    # Filtro Comentários
                    cols_c = ['text', 'posted_at', 'comment_url', 'author', 'owner_name', 'owner_profile_url']
                    if not df_comments.empty:
                        valid_c = [c for c in cols_c if c in df_comments.columns]
                        df_comments = df_comments[valid_c]

                    # 2. LIKES
                    status.write("👍 Extraindo Likes...")
                    run_likes = client.actor(ACTOR_LIKES).call(run_input={
                        "posts": [url_input], "maxItems": 1000
                    })
                    data_likes = client.dataset(run_likes["defaultDatasetId"]).list_items().items
                    
                    # Tratamento Likes
                    lista_likes_limpa = []
                    for item in data_likes:
                        actor = item.get('actor', {})
                        lista_likes_limpa.append({
                            "Nome": actor.get('name') or item.get('name'),
                            "Headline": actor.get('position') or item.get('headline'),
                            "Perfil URL": actor.get('linkedinUrl') or actor.get('profileUrl') or item.get('profileUrl'),
                            "Reação": item.get('reactionType'),
                            "Imagem": actor.get('pictureUrl') or item.get('pictureUrl')
                        })
                    df_likes = pd.DataFrame(lista_likes_limpa)

                    # 3. EXCEL
                    status.write("📊 Gerando Arquivo...")
                    buffer = io.BytesIO()
                    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                        if not df_comments.empty: df_comments.to_excel(writer, index=False, sheet_name='Comentarios')
                        if not df_likes.empty: df_likes.to_excel(writer, index=False, sheet_name='Likes')

                    # 4. CLAY (Sem nome de usuário específico)
                    if clay_url:
                        status.write("📡 Enviando para Clay...")
                        payload = {
                            "meta": {
                                "usuario": "Time Atlas", # Nome genérico
                                "data": datetime.now().isoformat(),
                                "link": url_input
                            },
                            "resumo": { "qtd_comentarios": len(df_comments), "qtd_likes": len(df_likes) },
                            "dados_comentarios": df_comments.to_dict(orient='records'),
                            "dados_likes": df_likes.to_dict(orient='records')
                        }
                        requests.post(clay_url, json=payload)

                    status.update(label="Concluído!", state="complete")
                    
                    # Métricas
                    c1, c2 = st.columns(2)
                    c1.metric("Comentários", len(df_comments))
                    c2.metric("Likes", len(df_likes))
                    
                    st.download_button("📥 Baixar Excel", data=buffer, file_name="Atlas_Dados.xlsx")
                    
                except Exception as e:
                    st.error(f"Erro: {e}")

if st.session_state.authenticated:
    main_app()
else:
    login_screen()
