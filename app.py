import streamlit as st
import datetime

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
# 2. BANCO DE DADOS SIMULADO (Memória)
# ==========================================
def inicializar_banco():
    # Tabela de Usuários
    if 'db_users' not in st.session_state:
        st.session_state['db_users'] = {
            "roberto@weg.net": {
                "nome": "Roberto",
                "senha": "WEG2026", # Senha padrão que força a troca
                "area": "Almoxarifado - WEN SZO",
                "role": "Admin",
                "ativo": True
            }
        }
    
    # Tabela de Solicitações de Acesso
    if 'db_requests' not in st.session_state:
        st.session_state['db_requests'] = []

    # Controle de Sessão Atual
    if 'authenticated' not in st.session_state:
        st.session_state['authenticated'] = False
    if 'must_change_password' not in st.session_state:
        st.session_state['must_change_password'] = False
    if 'current_user' not in st.session_state:
        st.session_state['current_user'] = None

inicializar_banco()

# ==========================================
# 3. FUNÇÕES DE AUTENTICAÇÃO
# ==========================================
def fazer_login(email, senha):
    usuario = st.session_state['db_users'].get(email)
    
    if usuario and usuario['ativo'] and usuario['senha'] == senha:
        st.session_state['authenticated'] = True
        st.session_state['current_user'] = {
            "email": email,
            "nome": usuario['nome'],
            "area": usuario['area'],
            "role": usuario['role']
        }
        # Regra de troca de senha obrigatória
        if senha == "WEG2026":
            st.session_state['must_change_password'] = True
        else:
            st.session_state['must_change_password'] = False
        return True
    return False

def fazer_logout():
    st.session_state['authenticated'] = False
    st.session_state['must_change_password'] = False
    st.session_state['current_user'] = None
    st.rerun()

# ==========================================
# 4. TELAS DE LOGIN E TROCA DE SENHA
# ==========================================
def render_login():
    # Centralizando a tela de login
    col1, col2, col3 = st.columns([1, 1.5, 1])
    
    with col2:
        st.write("<br><br>", unsafe_allow_html=True)
        try:
            st.image("logo_weg.png", width=200)
        except:
            st.markdown("### [LOGO WEG]")
            
        st.markdown("<h2 style='color: #00579D;'>Central de Alertas</h2>", unsafe_allow_html=True)
        
        # Abas de Login e Solicitação de Acesso
        aba_login, aba_solicitar = st.tabs(["🔐 Entrar", "📝 Solicitar Acesso"])
        
        # ABA 1: ENTRAR
        with aba_login:
            with st.form("form_login"):
                email = st.text_input("E-mail corporativo (@weg.net)")
                senha = st.text_input("Senha", type="password")
                btn_login = st.form_submit_button("Entrar", use_container_width=True)
                
                if btn_login:
                    if fazer_login(email, senha):
                        st.rerun()
                    else:
                        st.error("E-mail ou senha incorretos, ou usuário inativo.")
        
        # ABA 2: SOLICITAR ACESSO
        with aba_solicitar:
            with st.form("form_solicitacao"):
                req_nome = st.text_input("Nome Completo")
                req_email = st.text_input("E-mail (@weg.net)")
                req_area = st.text_input("Área/Setor")
                req_motivo = st.text_area("Motivo da solicitação")
                btn_solicitar = st.form_submit_button("Enviar Solicitação", use_container_width=True)
                
                if btn_solicitar:
                    if "@weg.net" not in req_email:
                        st.error("Por favor, utilize um e-mail válido da WEG (@weg.net).")
                    elif req_nome and req_email and req_area:
                        # Grava na "tabela" de requests pendentes
                        st.session_state['db_requests'].append({
                            "nome": req_nome,
                            "email": req_email,
                            "area": req_area,
                            "motivo": req_motivo,
                            "status": "pendente",
                            "data": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                        st.success("Solicitação enviada! Aguarde a aprovação do Administrador.")
                    else:
                        st.warning("Preencha todos os campos obrigatórios.")

def render_trocar_senha():
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.write("<br><br>", unsafe_allow_html=True)
        st.warning("⚠️ Troca de Senha Obrigatória")
        st.markdown("Como você está usando a senha padrão (`WEG2026`), é necessário cadastrar uma nova senha para acessar o sistema.")
        
        with st.form("form_troca_senha"):
            nova_senha = st.text_input("Nova Senha", type="password")
            confirma_senha = st.text_input("Confirmar Nova Senha", type="password")
            btn_salvar = st.form_submit_button("Salvar e Continuar", use_container_width=True)
            
            if btn_salvar:
                if len(nova_senha) < 6:
                    st.error("A nova senha deve ter pelo menos 6 caracteres.")
                elif nova_senha == "WEG2026":
                    st.error("A nova senha não pode ser igual à senha padrão.")
                elif nova_senha != confirma_senha:
                    st.error("As senhas não coincidem.")
                else:
                    # Atualiza no "Banco de Dados"
                    email_atual = st.session_state['current_user']['email']
                    st.session_state['db_users'][email_atual]['senha'] = nova_senha
                    # Libera o acesso
                    st.session_state['must_change_password'] = False
                    st.success("Senha alterada com sucesso!")
                    st.rerun()

# ==========================================
# 5. COMPONENTES DE LAYOUT (App Shell)
# ==========================================
def render_header():
    col1, col2, col3 = st.columns([8, 1, 2])
    with col1:
        st.title("Central de Alertas")
    with col2:
        st.markdown("<h3 style='text-align: right;'>🔔 <span style='color:red; font-size:14px;'>●</span></h3>", unsafe_allow_html=True)
    with col3:
        st.markdown(f"**👤 {st.session_state['current_user']['nome']}**<br><span style='font-size:12px; color:gray;'>{st.session_state['current_user']['area']}</span>", unsafe_allow_html=True)
    st.markdown("---")

def render_sidebar():
    try:
        st.sidebar.image("logo_weg.png", width=150)
    except:
        st.sidebar.markdown("**[LOGO WEG]**")
        
    st.sidebar.markdown("### 🚨 Navegação")
    
    opcoes_menu = ["Dashboard", "Problemas", "Minhas Ações", "Colaboradores", "Administração"]
    menu_selecionado = st.sidebar.radio("Selecione a página:", opcoes_menu, key="menu_lateral")
    
    st.sidebar.markdown("---")
    st.sidebar.caption(f"Logado como: **{st.session_state['current_user']['role']}**")
    
    if st.sidebar.button("Sair (Logout)", use_container_width=True):
        fazer_logout()
        
    st.sidebar.caption("© 2026 WEG - Almoxarifado")
    
    return menu_selecionado

# ==========================================
# 6. PÁGINAS DO SISTEMA
# ==========================================
def pagina_dashboard():
    st.header("📊 Dashboard")
    st.info("Visão geral dos alertas, problemas e KPIs. (Será construído no Step 11)")

def pagina_problemas():
    st.header("⚠️ Gestão de Problemas")
    st.info("Abertura, listagem e detalhe de problemas e alertas. (Será construído no Step 7)")
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
    
    st.subheader("Simulação de Banco de Dados (Debug temporário)")
    st.write("Usuários:", st.session_state['db_users'])
    st.write("Solicitações Pendentes:", st.session_state['db_requests'])

# ==========================================
# 7. CONTROLADOR PRINCIPAL (ROTEADOR)
# ==========================================
def main():
    # 1. Se não estiver autenticado, mostra a tela de Login
    if not st.session_state['authenticated']:
        render_login()
    
    # 2. Se estiver autenticado mas precisa trocar a senha
    elif st.session_state['must_change_password']:
        render_trocar_senha()
        
    # 3. Se estiver tudo OK, mostra o sistema
    else:
        render_header()
        pagina_atual = render_sidebar()
        
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

if __name__ == "__main__":
    main()
