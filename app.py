import streamlit as st
import datetime
import pandas as pd

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
    if 'db_users' not in st.session_state:
        st.session_state['db_users'] = {
            "roberto": {
                "nome": "Roberto",
                "senha": "WEG2026", 
                "area": "Almoxarifado - WEN SZO",
                "role": "Admin", # Papéis: Admin, Facilitador, User
                "ativo": True
            }
        }
    
    if 'db_requests' not in st.session_state:
        st.session_state['db_requests'] = []
        
    if 'request_counter' not in st.session_state:
        st.session_state['request_counter'] = 1

    if 'authenticated' not in st.session_state:
        st.session_state['authenticated'] = False
    if 'must_change_password' not in st.session_state:
        st.session_state['must_change_password'] = False
    if 'current_user' not in st.session_state:
        st.session_state['current_user'] = None

inicializar_banco()

# ==========================================
# 3. FUNÇÕES DE AUTENTICAÇÃO E ADMINISTRAÇÃO
# ==========================================
def fazer_login(usuario_login, senha):
    usuario_login = usuario_login.strip().lower() 
    usuario = st.session_state['db_users'].get(usuario_login)
    
    if usuario and usuario['ativo'] and usuario['senha'] == senha:
        st.session_state['authenticated'] = True
        st.session_state['current_user'] = {
            "login": usuario_login,
            "nome": usuario['nome'],
            "area": usuario['area'],
            "role": usuario['role']
        }
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

def aprovar_solicitacao(req_id):
    """Aprova acesso, cria o usuário e define senha WEG2026"""
    for req in st.session_state['db_requests']:
        if req['id'] == req_id:
            req['status'] = 'aprovado'
            st.session_state['db_users'][req['login']] = {
                "nome": req['nome'],
                "senha": "WEG2026",
                "area": req['area'],
                "role": "User", # Entra como usuário comum por padrão
                "ativo": True
            }
            break

def rejeitar_solicitacao(req_id):
    """Rejeita a solicitação de acesso"""
    for req in st.session_state['db_requests']:
        if req['id'] == req_id:
            req['status'] = 'rejeitado'
            break

# ==========================================
# 4. TELAS DE LOGIN, SOLICITAÇÃO E RESET
# ==========================================
def render_login():
    col1, col2, col3 = st.columns([1, 1.5, 1])
    
    with col2:
        st.write("<br><br>", unsafe_allow_html=True)
        try:
            st.image("logo_weg.png", width=200)
        except:
            st.markdown("### [LOGO WEG]")
            
        st.markdown("<h2 style='color: #00579D;'>Central de Alertas</h2>", unsafe_allow_html=True)
        
        aba_login, aba_solicitar, aba_reset = st.tabs(["🔐 Entrar", "📝 Solicitar Acesso", "🔑 Esqueci a Senha"])
        
        # ABA 1: ENTRAR
        with aba_login:
            with st.form("form_login"):
                usuario_login = st.text_input("Usuário WEG")
                senha = st.text_input("Senha", type="password")
                btn_login = st.form_submit_button("Entrar", use_container_width=True)
                
                if btn_login:
                    if fazer_login(usuario_login, senha):
                        st.rerun()
                    else:
                        st.error("Usuário ou senha incorretos, ou cadastro inativo.")
        
        # ABA 2: SOLICITAR ACESSO
        with aba_solicitar:
            with st.form("form_solicitacao"):
                req_nome = st.text_input("Nome Completo")
                req_usuario = st.text_input("Usuário WEG pretendido")
                req_area = st.text_input("Área/Setor")
                req_motivo = st.text_area("Motivo da solicitação")
                btn_solicitar = st.form_submit_button("Enviar Solicitação", use_container_width=True)
                
                if btn_solicitar:
                    if req_nome and req_usuario and req_area:
                        st.session_state['db_requests'].append({
                            "id": st.session_state['request_counter'],
                            "nome": req_nome,
                            "login": req_usuario.strip().lower(),
                            "area": req_area,
                            "motivo": req_motivo,
                            "status": "pendente",
                            "data": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                        })
                        st.session_state['request_counter'] += 1
                        st.success("Solicitação enviada! Aguarde a aprovação do Administrador.")
                    else:
                        st.warning("Preencha todos os campos obrigatórios.")
                        
        # ABA 3: ESQUECI A SENHA
        with aba_reset:
            st.info("Informe seu usuário para redefinir a senha de volta para o padrão (WEG2026).")
            with st.form("form_reset"):
                reset_usuario = st.text_input("Usuário WEG")
                btn_reset = st.form_submit_button("Redefinir Senha", use_container_width=True)
                
                if btn_reset:
                    user_clean = reset_usuario.strip().lower()
                    if user_clean in st.session_state['db_users']:
                        st.session_state['db_users'][user_clean]['senha'] = "WEG2026"
                        st.success(f"✅ Senha do usuário '{user_clean}' redefinida para **WEG2026**.")
                    else:
                        st.error("Usuário não encontrado no sistema.")

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
                    login_atual = st.session_state['current_user']['login']
                    st.session_state['db_users'][login_atual]['senha'] = nova_senha
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
    
    # Adicionado ícones simulados para melhor visual
    opcoes_menu = ["📊 Dashboard", "⚠️ Problemas", "✅ Minhas Ações", "👥 Colaboradores", "⚙️ Administração"]
    
    # Lógica de seleção limpa e segura (Evita erro de Streamlit key)
    menu_selecionado = st.sidebar.radio("Selecione a página:", opcoes_menu)
    
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
    st.header("Dashboard")
    st.info("Visão geral dos alertas, problemas e KPIs. (Será construído no Step 11)")

def pagina_problemas():
    st.header("Gestão de Problemas")
    st.info("Abertura, listagem e detalhe de problemas e alertas. (Será construído no Step 7)")

def pagina_acoes():
    st.header("Minhas Ações Corretivas")
    st.info("Lista de ações onde você é o responsável. (Será construído no Step 9)")

def pagina_colaboradores():
    st.header("👥 Base de Colaboradores")
    st.markdown("Lista oficial de todos os colaboradores com acesso ao sistema (Aprovados).")
    
    # Transforma o dict de usuários em uma tabela bonita usando Pandas
    df_users = pd.DataFrame.from_dict(st.session_state['db_users'], orient='index')
    # Reordenando as colunas e traduzindo para exibição
    df_display = df_users[['nome', 'area', 'role', 'ativo']].copy()
    df_display.columns = ['Nome Completo', 'Área / Setor', 'Nível de Acesso', 'Status Ativo']
    
    st.dataframe(df_display, use_container_width=True, hide_index=True)

def pagina_administracao():
    st.header("⚙️ Painel de Administração")
    
    # Bloqueio de Segurança (Somente Admin acessa)
    if st.session_state['current_user']['role'] != 'Admin':
        st.error("Acesso restrito: Somente administradores podem acessar esta página.")
        return
        
    st.markdown("Bem-vindo ao painel de gestão de acessos e configurações.")
    
    # CARTÃO 1: SOLICITAÇÕES PENDENTES
    st.subheader("📝 Solicitações de Acesso (Pendentes)")
    pendentes = [req for req in st.session_state['db_requests'] if req['status'] == 'pendente']
    
    if not pendentes:
        st.success("Nenhuma solicitação de acesso pendente no momento.")
    else:
        for req in pendentes:
            with st.expander(f"📌 {req['nome']} ({req['login']}) - {req['area']}", expanded=True):
                st.write(f"**Motivo:** {req['motivo']}")
                st.write(f"**Data da solicitação:** {req['data']}")
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    if st.button("✅ Aprovar", key=f"apr_{req['id']}", type="primary"):
                        aprovar_solicitacao(req['id'])
                        st.success(f"Aprovado! Atualize a página.")
                        st.rerun()
                with col2:
                    if st.button("❌ Rejeitar", key=f"rej_{req['id']}"):
                        rejeitar_solicitacao(req['id'])
                        st.warning(f"Rejeitado! Atualize a página.")
                        st.rerun()
                        
    st.markdown("---")
    
    # CARTÃO 2: HISTÓRICO DE SOLICITAÇÕES
    st.subheader("📜 Histórico de Solicitações")
    historico = [req for req in st.session_state['db_requests'] if req['status'] != 'pendente']
    
    if historico:
        df_hist = pd.DataFrame(historico)
        df_hist = df_hist[['nome', 'login', 'area', 'status', 'data']]
        df_hist.columns = ['Nome', 'Usuário', 'Área', 'Status', 'Data']
        
        # Função para colorir status
        def colorir_status(val):
            color = 'green' if val == 'aprovado' else 'red'
            return f'color: {color}; font-weight: bold;'
            
        st.dataframe(df_hist.style.applymap(colorir_status, subset=['Status']), use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum histórico disponível.")

# ==========================================
# 7. CONTROLADOR PRINCIPAL (ROTEADOR)
# ==========================================
def main():
    if not st.session_state['authenticated']:
        render_login()
    elif st.session_state['must_change_password']:
        render_trocar_senha()
    else:
        render_header()
        pagina_atual = render_sidebar()
        
        # Navegação baseada na string limpa de emojis
        if "Dashboard" in pagina_atual:
            pagina_dashboard()
        elif "Problemas" in pagina_atual:
            pagina_problemas()
        elif "Ações" in pagina_atual:
            pagina_acoes()
        elif "Colaboradores" in pagina_atual:
            pagina_colaboradores()
        elif "Administração" in pagina_atual:
            pagina_administracao()

if __name__ == "__main__":
    main()
