import streamlit as st

# ==========================================
# 1. CONFIGURAÇÃO DA PÁGINA (Identidade WEG)
# ==========================================
st.set_page_config(
    page_title="Central de Alertas - WEG",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# 2. INICIALIZAÇÃO DE VARIÁVEIS (Memória)
# ==========================================
# Estrutura segura para evitar o erro de mutação de chave de widget
if 'current_user' not in st.session_state:
    st.session_state['current_user'] = {
        "nome": "Roberto",
        "area": "Almoxarifado - WEN SZO",
        "role": "Admin"
    }

# ==========================================
# 3. COMPONENTES DE LAYOUT
# ==========================================
def render_header():
    """Renderiza o cabeçalho superior simulando sino de notificação e perfil"""
    col1, col2, col3 = st.columns([8, 1, 2])
    with col1:
        st.title("Central de Alertas")
    with col2:
        # Botão/Sino de notificação (simulado)
        st.markdown("<h3 style='text-align: right;'>🔔 <span style='color:red; font-size:14px;'>●</span></h3>", unsafe_allow_html=True)
    with col3:
        # Perfil do usuário
        st.markdown(f"**👤 {st.session_state['current_user']['nome']}**<br><span style='font-size:12px; color:gray;'>{st.session_state['current_user']['area']}</span>", unsafe_allow_html=True)
    st.markdown("---")

def render_sidebar():
    """Menu lateral de navegação integrado ao Streamlit"""
    
    # ==== CORREÇÃO DO LOGO AQUI ====
    # Agora ele procura o arquivo local que você subiu para o GitHub
    try:
        st.sidebar.image("logo_weg.png", width=150)
    except:
        st.sidebar.markdown("**[LOGO WEG]**") # Fallback caso a imagem ainda não tenha subido
    # ===============================
    
    st.sidebar.markdown("### 🚨 Navegação")
    
    opcoes_menu = [
        "Dashboard", 
        "Problemas", 
        "Minhas Ações", 
        "Colaboradores", 
        "Administração"
    ]
    
    # Usamos o st.sidebar.radio como navegador principal.
    menu_selecionado = st.sidebar.radio(
        "Selecione a página:",
        opcoes_menu,
        key="menu_lateral"
    )
    
    st.sidebar.markdown("---")
    st.sidebar.caption(f"Logado como: **{st.session_state['current_user']['role']}**")
    st.sidebar.caption("© 2026 WEG - Almoxarifado")
    
    return menu_selecionado

# ==========================================
# 4. PÁGINAS (Placeholders para os próximos passos)
# ==========================================
def pagina_dashboard():
    st.header("📊 Dashboard")
    st.info("Visão geral dos alertas, problemas e KPIs. (Será construído no Step 11)")

def pagina_problemas():
    st.header("⚠️ Gestão de Problemas")
    st.info("Abertura, listagem e detalhe de problemas e alertas. (Será construído no Step 7)")
    
    # Apenas como prova de conceito para sua requisição de guardar pesquisa
    pesquisa = st.text_input("Pesquisar problema:", key="pesquisa_problema_input")
    st.write(f"Você pesquisou por: {pesquisa}")

def pagina_acoes():
    st.header("✅ Minhas Ações Corretivas")
    st.info("Lista de ações onde você é o responsável. (Será construído no Step 9)")

def pagina_colaboradores():
    st.header("👥 Colaboradores")
    st.info("Gestão de perfis e áreas (CRUD de colaboradores). (Será construído no Step 5)")

def pagina_administracao():
    st.header("⚙️ Administração")
    st.info("Configurações de SLA e Facilitadores. (Será construído no Step 6 e 12)")

# ==========================================
# 5. CONTROLADOR PRINCIPAL (ROTEADOR)
# ==========================================
def main():
    # Renderiza Cabeçalho
    render_header()
    
    # Renderiza Menu Lateral e captura a página escolhida
    pagina_atual = render_sidebar()
    
    # Roteamento de páginas
    if pagina_atual == "Dashboard":
        pagina_dashboard()
    elif pagina_atual == "Problemas":
        pagina_problemas()
    elif pagina_atual == "Minhas Ações":
        pagina_acoes()
    elif pagina_atual == "Colaboradores":
        pagina_colaboradores()
    elif pagina_atual == "Administração":
        pagina_administracao()

# Executa o aplicativo
if __name__ == "__main__":
    main()
