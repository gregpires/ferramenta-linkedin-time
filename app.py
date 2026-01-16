import streamlit as st
from apify_client import ApifyClient
import pandas as pd
import io
import time

# --- 1. CONFIGURAÇÃO (Obrigatório ser a primeira linha) ---
st.set_page_config(page_title="Atlas System", page_icon="🔒", layout="centered")

# --- 2. CSS VISUAL (Para deixar o login bonito e centralizado) ---
st.markdown("""
<style>
    /* Fundo geral escuro */
    .stApp {
        background-color: #1E1E1E;
        color: white;
    }
    
    /* Esconde menu padrão do Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Caixa de Login Centralizada */
    .login-container {
        background-color: #2D2D2D;
        padding: 40px;
        border-radius: 15px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.5);
        border: 1px solid #444;
        text-align: center;
        margin-top: 50px;
    }
    
    /* Inputs estilizados */
    .stTextInput > div > div > input {
        background-color: #404040;
        color: white;
        border: 1px solid #555;
    }
    
    /* Cores de destaque */
    h1 { color: #FF4B4B !important; }
</style>
""", unsafe_allow_html=True)

# --- 3. CONTROLE DE SESSÃO ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

# --- 4. TELA DE LOGIN ---
def login_screen():
    # Colunas para centralizar
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # HTML para a caixa visual
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        st.title("🔒 ATLAS SYSTEM")
        st.markdown("Acesso Restrito")
        
        # Campo de senha
        senha = st.text_input("Senha", type="password", placeholder="Digite a senha...")
        
        if st.button("ACESSAR", type="primary"):
            # --- AQUI ESTÁ A SEGURANÇA DINÂMICA ---
            # O código busca a senha definida nos Secrets.
            # Se a chave não existir, ele avisa o erro.
            if "SENHA_DO_SISTEMA" not in st.secrets:
                st.error("ERRO: A senha não foi configurada nos Secrets!")
            elif senha == st.secrets["SENHA_DO_SISTEMA"]:
                st.session_state.authenticated = True
                st.success("Logado com sucesso!")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("Senha incorreta")
        
        st.markdown('</div>', unsafe_allow_html=True)

# --- 5. O APP PRINCIPAL (Extrator) ---
def main_app():
    # Botão Sair no canto
    col_out = st.columns([6, 1])
    with col_out[1]:
        if st.button("Sair"):
            st.session_state.authenticated = False
            st.rerun()

    st.title("🚀 Extrator LinkedIn")
    
    # Verifica Token do Apify
    if "APIFY_TOKEN" in st.secrets:
        api_token = st.secrets["APIFY_TOKEN"]
    else:
        st.error("ERRO: Configure o APIFY_TOKEN nos Secrets!")
        st.stop()
        
    url_input = st.text_input("Link do Post:", placeholder="https://linkedin.com/...")
    
    if st.button("Extrair Dados"):
        if not url_input:
            st.warning("Cole o link primeiro.")
        else:
            with st.status("Processando...", expanded=True) as status:
                try:
                    # Conexão Apify
                    client = ApifyClient(api_token)
                    
                    # Configuração para o ator datadoping
                    run_input = { 
                        "posts": [url_input], 
                        "maxComments": 100, 
                        "minDelay": 2, 
                        "maxDelay": 5 
                    }
                    
                    status.write("🤖 Robô trabalhando...")
                    run = client.actor("datadoping/linkedin-post-comments-scraper").call(run_input=run_input)
                    
                    status.write("📦 Baixando dados...")
                    dataset_items = client.dataset(run["defaultDatasetId"]).list_items().items
                    
                    if dataset_items:
                        df = pd.DataFrame(dataset_items)
                        
                        # Filtro de colunas (As que você pediu)
                        cols = ['text', 'posted_at', 'comment_url', 'author', 'total_reactions', 'total_replies', 'owner_name', 'owner_profile_url', 'input']
                        cols_final = [c for c in cols if c in df.columns]
                        df = df[cols_final]
                        
                        # Gera o Excel em memória
                        buffer = io.BytesIO()
                        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                            df.to_excel(writer, index=False)
                            
                        status.update(label="Concluído!", state="complete")
                        
                        st.success(f"{len(df)} comentários extraídos.")
                        st.download_button("📥 Download Excel", data=buffer, file_name="linkedin_atlas.xlsx")
                    else:
                        status.update(label="Sem dados encontrados", state="error")
                        
                except Exception as e:
                    st.error(f"Erro: {e}")

# --- 6. ROTEADOR DE TELAS ---
if st.session_state.authenticated:
    main_app()
else:
    login_screen()
