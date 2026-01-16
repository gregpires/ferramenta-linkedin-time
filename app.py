import streamlit as st
from apify_client import ApifyClient
import pandas as pd
import io
import time
import requests
from datetime import datetime

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(page_title="Atlas System", page_icon="🔒", layout="centered")

# --- 2. CONFIGURAÇÃO DOS ATORES ---
# Actor 1: Comentários (DataDoping)
ACTOR_COMMENTS = "datadoping/linkedin-post-comments-scraper"
# Actor 2: Likes/Reações (HarvestAPI)
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
    .stMetric { background-color: #333; padding: 10px; border-radius: 5px; text-align: center; }
</style>
""", unsafe_allow_html=True)

# --- 4. SESSÃO ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'username' not in st.session_state:
    st.session_state.username = None

# --- 5. TELA DE LOGIN ---
def login_screen():
    # Verifica lista de usuários nos Secrets
    if "usuarios" in st.secrets:
        USUARIOS_PERMITIDOS = st.secrets["usuarios"]
    else:
        st.error("⚠️ Configure os [usuarios] nos Secrets do Streamlit!")
        st.stop()

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        st.title("🔒 ATLAS SYSTEM")
        st.markdown("Intelligence Login")
        usuario = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password")
        
        if st.button("ACESSAR", type="primary"):
            if usuario in USUARIOS_PERMITIDOS and USUARIOS_PERMITIDOS[usuario] == senha:
                st.session_state.authenticated = True
                st.session_state.username = usuario
                st.rerun()
            else:
                st.error("Credenciais inválidas.")
        st.markdown('</div>', unsafe_allow_html=True)

# --- 6. APP PRINCIPAL ---
def main_app():
    col_info, col_out = st.columns([6, 1])
    with col_info:
        st.success(f"Logado como: **{st.session_state.username}**")
    with col_out:
        if st.button("Sair"):
            st.session_state.authenticated = False
            st.rerun()

    st.title("🚀 Extrator Full LinkedIn")
    st.markdown("Extrai **Comentários** e **Likes (Reações)** do post simultaneamente.")

    # Verificação de Token
    if "APIFY_TOKEN" not in st.secrets:
        st.error("Token Apify não configurado.")
        st.stop()
        
    api_token = st.secrets["APIFY_TOKEN"]
    clay_url = st.secrets.get("CLAY_WEBHOOK", "") 

    url_input = st.text_input("Link do Post:", placeholder="https://www.linkedin.com/posts/...")
    
    if st.button("Iniciar Extração Completa", type="primary"):
        if not url_input:
            st.warning("Por favor, insira um link.")
        else:
            with st.status("🔍 Processando Inteligência...", expanded=True) as status:
                try:
                    client = ApifyClient(api_token)
                    
                    # --- FASE 1: COMENTÁRIOS (DataDoping) ---
                    status.write("💬 Extraindo Comentários...")
                    run_comments = client.actor(ACTOR_COMMENTS).call(run_input={ 
                        "posts": [url_input], 
                        "maxComments": 200, 
                        "minDelay": 1, 
                        "maxDelay": 4 
                    })
                    data_comments = client.dataset(run_comments["defaultDatasetId"]).list_items().items
                    df_comments = pd.DataFrame(data_comments)
                    
                    # Filtra colunas de comentários
                    cols_c = ['text', 'posted_at', 'comment_url', 'author', 'owner_name', 'owner_profile_url']
                    if not df_comments.empty:
                        # Pega apenas as colunas que existirem no retorno
                        valid_c = [c for c in cols_c if c in df_comments.columns]
                        df_comments = df_comments[valid_c]

                    # --- FASE 2: LIKES / REAÇÕES (HarvestAPI) ---
                    status.write("👍 Extraindo Likes e Reações...")
                    # A HarvestAPI geralmente usa "posts" ou "urls" como lista
                    run_likes = client.actor(ACTOR_LIKES).call(run_input={
                        "posts": [url_input],  # Input padrão para mass scrapers
                        "maxItems": 1000       # Limite de segurança
                    })
                    data_likes = client.dataset(run_likes["defaultDatasetId"]).list_items().items
                    
                    # Tratamento de dados dos Likes (O retorno é aninhado dentro de 'actor')
                    lista_likes_limpa = []
                    for item in data_likes:
                        # Tenta pegar dados do 'actor' se existir, senão pega do raiz
                        actor = item.get('actor', {})
                        lista_likes_limpa.append({
                            "Nome": actor.get('name') or item.get('name'),
                            "Headline": actor.get('position') or item.get('headline'),
                            "Perfil URL": actor.get('linkedinUrl') or actor.get('profileUrl') or item.get('profileUrl'),
                            "Reação": item.get('reactionType'),
                            "Imagem": actor.get('pictureUrl') or item.get('pictureUrl')
                        })
                    
                    df_likes = pd.DataFrame(lista_likes_limpa)

                    # --- FASE 3: CONSOLIDAR EXCEL ---
                    status.write("📊 Gerando Relatório Unificado...")
                    buffer = io.BytesIO()
                    
                    # Cria o Excel com 2 abas
                    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                        # Aba 1: Comentários
                        if not df_comments.empty:
                            df_comments.to_excel(writer, index=False, sheet_name='Comentarios')
                        else:
                            # Cria aba vazia com aviso se não tiver dados
                            pd.DataFrame({'Aviso': ['Sem comentários encontrados']}).to_excel(writer, sheet_name='Comentarios')
                            
                        # Aba 2: Likes
                        if not df_likes.empty:
                            df_likes.to_excel(writer, index=False, sheet_name='Likes')
                        else:
                            pd.DataFrame({'Aviso': ['Sem likes encontrados']}).to_excel(writer, sheet_name='Likes')

                    # --- FASE 4: ENVIAR PARA CLAY ---
                    if clay_url:
                        status.write("📡 Enviando para Clay...")
                        payload = {
                            "meta": {
                                "usuario": st.session_state.username,
                                "data_extracao": datetime.now().isoformat(),
                                "link_post": url_input
                            },
                            "resumo": {
                                "qtd_comentarios": len(df_comments),
                                "qtd_likes": len(df_likes)
                            },
                            "dados_comentarios": df_comments.to_dict(orient='records'),
                            "dados_likes": df_likes.to_dict(orient='records')
                        }
                        try:
                            r = requests.post(clay_url, json=payload)
                            if r.status_code == 200:
                                status.write("✅ Clay recebeu os dados!")
                            else:
                                status.warning(f"Erro no Clay: {r.status_code}")
                        except:
                            status.warning("Falha na conexão com Clay.")

                    status.update(label="Concluído!", state="complete")
                    
                    # Mostra números na tela
                    col_a, col_b = st.columns(2)
                    col_a.metric("Comentários Extraídos", len(df_comments))
                    col_b.metric("Likes Extraídos", len(df_likes))
                    
                    # Botão Download
                    st.download_button(
                        label="📥 Baixar Excel Completo (Comentários + Likes)",
                        data=buffer,
                        file_name=f"Atlas_Full_{st.session_state.username}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                    
                except Exception as e:
                    status.update(label="Erro Crítico", state="error")
                    st.error(f"Erro detalhado: {e}")

# --- ROTEADOR ---
if st.session_state.authenticated:
    main_app()
else:
    login_screen()


