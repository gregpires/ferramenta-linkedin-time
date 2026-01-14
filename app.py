import streamlit as st
from apify_client import ApifyClient
import pandas as pd
import io
import time

# --- 1. Configurações da Página (Deve ser a primeira linha) ---
st.set_page_config(page_title="Atlas Extractor", page_icon="🌐", layout="centered")

# --- 2. CSS CUSTOMIZADO (Para deixar bonito) ---
st.markdown("""
<style>
    /* Esconde o menu hamburger e rodapé padrão do Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Estiliza o Container de Login */
    .login-box {
        padding: 2rem;
        border-radius: 10px;
        background-color: #f0f2f6;
        margin-top: 50px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        text-align: center;
    }
    
    /* Título Estilizado */
    h1 {
        color: #0e1117;
        font-family: 'Helvetica Neue', sans-serif;
    }
    
    /* Botões personalizados */
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
        background-color: #FF4B4B; 
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. Gerenciamento de Estado (Session State) ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

# --- 4. FUNÇÃO: TELA DE LOGIN ---
def login_page():
    st.markdown("<br><br>", unsafe_allow_html=True) # Espaço
    
    # Criamos colunas para centralizar o cartão de login
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("<div class='login-box'>", unsafe_allow_html=True)
        st.title("🔒 Atlas Access")
        st.markdown("Área restrita para o time.")
        
        senha = st.text_input("Senha de Acesso", type="password", placeholder="Digite a senha aqui...")
        
        if st.button("Entrar"):
            if senha == "Atlas@1234":
                st.session_state.authenticated = True
                st.success("Acesso autorizado! Carregando...")
                time.sleep(1)
                st.rerun() # Recarrega a página para ir pro App
            else:
                st.error("Senha incorreta.")
        
        st.markdown("</div>", unsafe_allow_html=True)

# --- 5. FUNÇÃO: O APP PRINCIPAL (Seu extrator) ---
def main_app():
    # Botão de Sair no topo direito
    col_logout = st.columns([8, 1])
    with col_logout[1]:
        if st.button("Sair"):
            st.session_state.authenticated = False
            st.rerun()

    st.title("💼 Extrator LinkedIn")
    st.markdown("---")
    
    # Verifica Token
    if "APIFY_TOKEN" in st.secrets:
        api_token = st.secrets["APIFY_TOKEN"]
    else:
        st.error("ERRO: Token não configurado.")
        st.stop()

    actor_id = "datadoping/linkedin-post-comments-scraper"

    # Input e Botão
    url_input = st.text_input("Cole o link do Post:", placeholder="https://www.linkedin.com/posts/...")
    
    if st.button("🚀 Extrair Dados", type="primary"):
        if not url_input:
            st.warning("Cole o link primeiro.")
        else:
            status = st.status("Iniciando processo...", expanded=True)
            try:
                status.write("🔌 Conectando ao Apify...")
                client = ApifyClient(api_token)
                
                run_input = {
                    "posts": [url_input], 
                    "maxComments": 100,    
                    "minDelay": 2,
                    "maxDelay": 5
                }
                
                status.write("🤖 Rodando agente inteligente...")
                run = client.actor(actor_id).call(run_input=run_input)
                
                status.write("📦 Coletando e filtrando dados...")
                dataset_items = client.dataset(run["defaultDatasetId"]).list_items().items
                
                if dataset_items:
                    df = pd.DataFrame(dataset_items)
                    
                    # Filtro de colunas
                    colunas_desejadas = ['text', 'posted_at', 'comment_url', 'author', 'total_reactions', 'total_replies', 'owner_name', 'owner_profile_url', 'input']
                    colunas_finais = [col for col in colunas_desejadas if col in df.columns]
                    df_filtrado = df[colunas_finais]
                    
                    buffer = io.BytesIO()
                    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                        df_filtrado.to_excel(writer, index=False, sheet_name='Dados')
                    
                    status.update(label="✅ Concluído!", state="complete", expanded=False)
                    
                    st.success(f"Sucesso! {len(dataset_items)} comentários extraídos.")
                    st.download_button("📥 Baixar Excel", data=buffer, file_name="linkedin_atlas.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                else:
                    status.update(label="⚠️ Sem dados", state="error")
                    st.warning("Nenhum dado encontrado.")
                    
            except Exception as e:
                status.update(label="❌ Erro", state="error")
                st.error(f"Erro: {e}")

# --- 6. CONTROLE DE FLUXO ---
if st.session_state.authenticated:
    main_app()
else:
    login_page()
