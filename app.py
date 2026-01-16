import streamlit as st
from apify_client import ApifyClient
import pandas as pd
import io
import time
import requests
from datetime import datetime

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(page_title="Atlas Intelligence", page_icon="🌐", layout="centered")

# --- 2. ATORES (ROBÔS) ---
ACTOR_COMMENTS = "datadoping/linkedin-post-comments-scraper"
ACTOR_LIKES = "harvestapi/linkedin-post-reactions"

# --- 3. CSS PREMIUM (GLASSMORPHISM) ---
st.markdown("""
<style>
    /* Importando Fonte Moderna (Inter) */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Fundo Gradiente Elegante */
    .stApp {
        background: radial-gradient(circle at 50% -20%, #2b2d42, #1a1b26, #0d0e12);
        color: #ffffff;
    }

    /* Esconde elementos padrão do Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* ESTILO DOS CARDS (Efeito Vidro) */
    .glass-card {
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 40px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
        margin-top: 20px;
        text-align: center;
    }

    /* Títulos */
    h1 {
        font-weight: 700;
        letter-spacing: -1px;
        color: #ffffff !important;
        margin-bottom: 0.5rem;
    }
    
    .subtitle {
        color: #a1a1aa;
        font-size: 0.9rem;
        margin-bottom: 2rem;
    }

    /* Inputs Customizados */
    .stTextInput > div > div > input {
        background-color: rgba(0, 0, 0, 0.3);
        color: white;
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 8px;
        height: 45px;
        padding-left: 15px;
    }
    .stTextInput > div > div > input:focus {
        border-color: #FF4B4B;
        box-shadow: 0 0 0 1px #FF4B4B;
    }

    /* Botões */
    .stButton > button {
        background: linear-gradient(90deg, #FF4B4B 0%, #FF1E1E 100%);
        color: white;
        border: none;
        border-radius: 8px;
        height: 45px;
        font-weight: 600;
        width: 100%;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(255, 75, 75, 0.3);
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(255, 75, 75, 0.4);
    }

    /* Métricas */
    div[data-testid="stMetricValue"] {
        font-size: 24px;
        color: #FF4B4B;
    }
    div[data-testid="stMetricLabel"] {
        color: #a1a1aa;
    }
    
    /* Alerts/Status */
    .stStatus {
        background-color: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)

# --- 4. SESSÃO ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

# --- 5. TELA DE LOGIN ---
def login_screen():
    if "SENHA_ACESSO" not in st.secrets:
        st.error("⚠️ Configure a SENHA_ACESSO nos Secrets!")
        st.stop()

    # Centralização Vertical e Horizontal
    col1, col2, col3 = st.columns([1, 4, 1])
    
    with col2:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("# ATLAS SYSTEM")
        st.markdown('<p class="subtitle">Intelligence & Data Extraction Suite</p>', unsafe_allow_html=True)
        
        senha = st.text_input("Credencial de Acesso", type="password", placeholder="••••••••")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button("ACESSAR PAINEL"):
            if senha == st.secrets["SENHA_ACESSO"]:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Acesso negado.")
        
        st.markdown('</div>', unsafe_allow_html=True)

# --- 6. APP PRINCIPAL ---
def main_app():
    # Header minimalista
    c1, c2 = st.columns([8, 1])
    with c2:
        if st.button("Sair", type="secondary"):
            st.session_state.authenticated = False
            st.rerun()

    st.markdown("# 🚀 Atlas Intelligence")
    st.markdown('<p class="subtitle" style="text-align: left;">Extração unificada de Comentários e Reações do LinkedIn.</p>', unsafe_allow_html=True)

    # Verifica Tokens
    if "APIFY_TOKEN" not in st.secrets:
        st.error("Token Apify ausente.")
        st.stop()
    
    api_token = st.secrets["APIFY_TOKEN"]
    clay_url = st.secrets.get("CLAY_WEBHOOK", "") 

    # Área de Input com estilo Glass
    st.markdown('<div class="glass-card" style="padding: 20px; margin-bottom: 20px; text-align: left;">', unsafe_allow_html=True)
    url_input = st.text_input("Cole a URL do Post", placeholder="https://www.linkedin.com/posts/...")
    st.markdown('</div>', unsafe_allow_html=True)

    if st.button("INICIAR EXTRAÇÃO GLOBAL"):
        if not url_input:
            st.warning("⚠️ O campo de link está vazio.")
        else:
            with st.status("⚡ Processando...", expanded=True) as status:
                try:
                    client = ApifyClient(api_token)
                    
                    # 1. COMENTÁRIOS
                    status.write("💬 Coletando Comentários...")
                    run_c = client.actor(ACTOR_COMMENTS).call(run_input={ 
                        "posts": [url_input], "maxComments": 200, "minDelay": 1, "maxDelay": 4 
                    })
                    data_c = client.dataset(run_c["defaultDatasetId"]).list_items().items
                    df_c = pd.DataFrame(data_c)
                    
                    # Filtro
                    cols_c = ['text', 'posted_at', 'comment_url', 'author', 'owner_name', 'owner_profile_url']
                    if not df_c.empty:
                        df_c = df_c[[c for c in cols_c if c in df_c.columns]]

                    # 2. LIKES
                    status.write("👍 Coletando Reações...")
                    run_l = client.actor(ACTOR_LIKES).call(run_input={
                        "posts": [url_input], "maxItems": 1000
                    })
                    data_l = client.dataset(run_l["defaultDatasetId"]).list_items().items
                    
                    # Tratamento
                    lista_l = []
                    for item in data_l:
                        actor = item.get('actor', {})
                        lista_l.append({
                            "Nome": actor.get('name') or item.get('name'),
                            "Headline": actor.get('position') or item.get('headline'),
                            "Perfil URL": actor.get('linkedinUrl') or actor.get('profileUrl') or item.get('profileUrl'),
                            "Reação": item.get('reactionType'),
                        })
                    df_l = pd.DataFrame(lista_l)

                    # 3. EXCEL
                    status.write("📊 Compilando Excel...")
                    buffer = io.BytesIO()
                    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                        if not df_c.empty: df_c.to_excel(writer, index=False, sheet_name='Comentarios')
                        else: pd.DataFrame(['Sem dados']).to_excel(writer, sheet_name='Comentarios')
                        
                        if not df_l.empty: df_l.to_excel(writer, index=False, sheet_name='Likes')
                        else: pd.DataFrame(['Sem dados']).to_excel(writer, sheet_name='Likes')

                    # 4. CLAY
                    if clay_url:
                        status.write("📡 Sincronizando com Clay...")
                        payload = {
                            "meta": { "usuario": "Time Atlas", "data": datetime.now().isoformat(), "link": url_input },
                            "resumo": { "qtd_comentarios": len(df_c), "qtd_likes": len(df_l) },
                            "dados_comentarios": df_c.to_dict(orient='records'),
                            "dados_likes": df_l.to_dict(orient='records')
                        }
                        requests.post(clay_url, json=payload)

                    status.update(label="Processo Concluído com Sucesso", state="complete")
                    
                    # Dashboard de Resultados
                    st.markdown("<br>", unsafe_allow_html=True)
                    m1, m2 = st.columns(2)
                    m1.metric("Comentários", len(df_c))
                    m2.metric("Reações", len(df_l))
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.download_button("📥 BAIXAR RELATÓRIO COMPLETO", data=buffer, file_name="Atlas_Report.xlsx")

                except Exception as e:
                    st.error(f"Erro na operação: {e}")

# --- ROTEADOR ---
if st.session_state.authenticated:
    main_app()
else:
    login_screen()
