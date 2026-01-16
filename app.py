import streamlit as st
from apify_client import ApifyClient
import pandas as pd
import io
import time

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(page_title="Atlas System", page_icon="🔒", layout="centered")

# --- 2. CSS VISUAL (ALTO CONTRASTE) ---
st.markdown("""
<style>
    /* Fundo Geral: Preto Suave (Melhor para leitura) */
    .stApp {
        background-color: #121212;
        color: #FFFFFF;
    }
    
    /* Esconde itens padrões do Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Caixa de Login: Cinza escuro com borda clara */
    .login-container {
        background-color: #1E1E1E;
        padding: 40px;
        border-radius: 12px;
        border: 1px solid #333333;
        box-shadow: 0 4px 20px rgba(0,0,0,0.6);
        text-align: center;
        margin-top: 50px;
    }
    
    /* Inputs: Fundo escuro, Texto Branco, Borda Visível */
    .stTextInput > div > div > input {
        background-color: #262626;
        color: #FFFFFF !important;
        border: 1px solid #4A4A4A;
        caret-color: #FF4B4B; /* Cor do cursor piscando */
    }
    
    /* Títulos e Textos */
    h1 { color: #FFFFFF !important; font-weight: 700; }
    p { color: #E0E0E0 !important; } /* Cinza bem claro para descrições */
    
    /* Botões: Destaque vermelho */
    .stButton > button {
        background-color: #FF4B4B;
        color: white;
        border: none;
        font-weight: bold;
    }
    .stButton > button:hover {
        background-color: #FF2B2B;
        border: 1px solid white;
    }
    
    /* Mensagens de Erro/Sucesso mais legíveis */
    .stAlert {
        background-color: #262626;
        color: white;
        border: 1px solid #444;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. CONTROLE DE SESSÃO ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

# --- 4. TELA DE LOGIN ---
def login_screen():
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        st.title("ATLAS SYSTEM")
        st.markdown("Acesso Restrito ao Time")
        
        senha = st.text_input("Senha de Acesso", type="password", placeholder="Digite aqui...")
        
        if st.button("ENTRAR ACESSO", type="primary"):
            # Verifica se a senha está nos Secrets (Dinâmico)
            if "SENHA_DO_SISTEMA" not in st.secrets:
                st.error("ERRO CONFIG: Senha não definida nos Secrets!")
            elif senha == st.secrets["SENHA_DO_SISTEMA"]:
                st.session_state.authenticated = True
                st.success("Acesso Liberado!")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("Senha incorreta.")
        
        st.markdown('</div>', unsafe_allow_html=True)

# --- 5. O APP PRINCIPAL ---
def main_app():
    col_out = st.columns([6, 1])
    with col_out[1]:
        if st.button("Sair"):
            st.session_state.authenticated = False
            st.rerun()

    st.title("🚀 Extrator LinkedIn")
    st.markdown("Cole o link abaixo para extrair comentários automaticamente.")
    
    # Verifica Token
    if "APIFY_TOKEN" in st.secrets:
        api_token = st.secrets["APIFY_TOKEN"]
    else:
        st.error("ERRO: Token do Apify não configurado.")
        st.stop()
        
    url_input = st.text_input("Link do Post:", placeholder="https://linkedin.com/posts/...")
    
    if st.button("INICIAR EXTRAÇÃO", type="primary"):
        if not url_input:
            st.warning("⚠️ Cole o link antes de clicar.")
        else:
            with st.status("🔄 Processando...", expanded=True) as status:
                try:
                    client = ApifyClient(api_token)
                    
                    # Input para o ator
                    run_input = { 
                        "posts": [url_input], 
                        "maxComments": 100, 
                        "minDelay": 2, 
                        "maxDelay": 5 
                    }
                    
                    status.write("🤖 Conectando ao Robô...")
                    run = client.actor("datadoping/linkedin-post-comments-scraper").call(run_input=run_input)
                    
                    status.write("📦 Baixando dados...")
                    dataset_items = client.dataset(run["defaultDatasetId"]).list_items().items
                    
                    if dataset_items:
                        df = pd.DataFrame(dataset_items)
                        
                        # Filtro de Colunas
                        cols = ['text', 'posted_at', 'comment_url', 'author', 'total_reactions', 'total_replies', 'owner_name', 'owner_profile_url', 'input']
                        cols_final = [c for c in cols if c in df.columns]
                        df = df[cols_final]
                        
                        buffer = io.BytesIO()
                        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                            df.to_excel(writer, index=False)
                            
                        status.update(label="✅ Finalizado!", state="complete")
                        
                        st.success(f"Sucesso! {len(df)} comentários encontrados.")
                        st.download_button("📥 BAIXAR EXCEL AGORA", data=buffer, file_name="linkedin_atlas.xlsx")
                    else:
                        status.update(label="❌ Sem dados", state="error")
                        st.error("O robô rodou mas não achou comentários. Verifique o link.")
                        
                except Exception as e:
                    st.error(f"Erro técnico: {e}")

# --- 6. ROTEADOR ---
if st.session_state.authenticated:
    main_app()
else:
    login_screen()

