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
                "email": "roberto@weg.net",
                "senha": "WEG2026", 
                "area": "Almoxarifado - WEN SZO",
                "role": "Admin", 
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
    
    if usuario and usuario.get('ativo', True) and usuario.get('senha') == senha:
        st.session_state['authenticated'] = True
        st.session_state['current_user'] = {
            "login": usuario_login,
            "nome": usuario.get('nome', usuario_login),
            "area": usuario.get('area', 'Não definida'),
            "role": usuario.get('role', 'User')
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
    for req in st.session_state['db_requests']:
        if req['id'] == req_id:
            req['status'] = 'aprovado'
            email_completo = req['email'].strip().lower()
            login_extraido = email_completo.split('@')[0]
            
            st.session_state['db_users'][login_extraido] = {
                "nome": req['nome'],
                "email": email_completo,
                "senha": "WEG2026",
                "area": "A definir", 
                "role": "User", 
                "ativo": True
            }
            break

def rejeitar_solicitacao(req_id):
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
        
        with aba_solicitar:
            with st.form("form_solicitacao"):
                req_nome = st.text_input("Nome Completo")
                req_email = st.text_input("E-mail corporativo (@weg.net)")
                btn_solicitar = st.form_submit_button("Enviar Solicitação", use_container_width=True)
                
                if btn_solicitar:
                    if req_nome and req_email:
                        st.session_state['db_requests'].append({
                            "id": st.session_state['request_counter'],
                            "nome": req_nome,
                            "email": req_email,
                            "status": "pendente",
                            "data": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                        })
                        st.session_state['request_counter'] += 1
                        st.success("Solicitação enviada! Aguarde a aprovação do Administrador.")
                    else:
                        st.warning("Preencha todos os campos obrigatórios.")
                        
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
    
    opcoes_menu = ["📊 Dashboard", "⚠️ Problemas", "✅ Minhas Ações", "👥 Colaboradores", "⚙️ Administração"]
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
    st.header("👥 Gestão de Colaboradores")
    
    is_admin = st.session_state['current_user']['role'] == 'Admin'
    
    if is_admin:
        tab1, tab2, tab3 = st.tabs(["📋 Lista de Colaboradores", "➕ Adicionar Novo", "✏️ Editar / Desativar"])
    else:
        tab1, = st.tabs(["📋 Lista de Colaboradores"])
    
    # ABA 1: LISTA (Visível para todos)
    with tab1:
        lista_usuarios = []
        for login, dados in st.session_state['db_users'].items():
            u = dados.copy()
            u['login'] = login
            # DEFESA CONTRA FANTASMAS DA SESSÃO ANTIGA:
            u['email'] = u.get('email', f"{login}@weg.net")
            u['ativo'] = u.get('ativo', True)
            u['role'] = u.get('role', 'User')
            u['area'] = u.get('area', 'Não definida')
            u['nome'] = u.get('nome', login)
            lista_usuarios.append(u)
            
        df_users = pd.DataFrame(lista_usuarios)
        
        if not df_users.empty:
            df_display = df_users[['login', 'nome', 'email', 'area', 'role', 'ativo']].copy()
            df_display.columns = ['Usuário', 'Nome Completo', 'E-mail', 'Área / Setor', 'Papel', 'Status Ativo']
            
            def colorir_ativo(val):
                if isinstance(val, bool):
                    color = 'green' if val else 'red'
                    return f'color: {color}; font-weight: bold;'
                return ''
                
            st.dataframe(df_display.style.applymap(colorir_ativo, subset=['Status Ativo']), use_container_width=True, hide_index=True)
        else:
            st.warning("Nenhum usuário cadastrado.")

    # ABAS RESTRITAS PARA ADMIN
    if is_admin:
        # ABA 2: ADICIONAR NOVO
        with tab2:
            st.markdown("Adicione um colaborador manualmente ao sistema. A senha inicial será `WEG2026`.")
            with st.form("form_add_colab"):
                col1, col2 = st.columns(2)
                with col1:
                    novo_nome = st.text_input("Nome Completo*")
                    novo_email = st.text_input("E-mail (@weg.net)*")
                with col2:
                    novo_area = st.text_input("Área / Setor*")
                    novo_papel = st.selectbox("Nível de Acesso*", ["User", "Facilitador", "Admin"])
                
                btn_add = st.form_submit_button("Salvar Colaborador")
                if btn_add:
                    if novo_nome and novo_email and novo_area:
                        novo_login = novo_email.strip().lower().split('@')[0]
                        if novo_login in st.session_state['db_users']:
                            st.error(f"O usuário '{novo_login}' já existe no sistema!")
                        else:
                            st.session_state['db_users'][novo_login] = {
                                "nome": novo_nome,
                                "email": novo_email,
                                "senha": "WEG2026",
                                "area": novo_area,
                                "role": novo_papel,
                                "ativo": True
                            }
                            st.success(f"Colaborador {novo_nome} adicionado com sucesso! Atualize a página.")
                    else:
                        st.warning("Preencha todos os campos obrigatórios.")
                        
        # ABA 3: EDITAR / DESATIVAR
        with tab3:
            st.markdown("Selecione um usuário abaixo para editar suas informações ou desativar o seu acesso.")
            
            logins_disponiveis = list(st.session_state['db_users'].keys())
            usuario_selecionado = st.selectbox("Selecione o Usuário:", logins_disponiveis)
            
            if usuario_selecionado:
                user_data = st.session_state['db_users'][usuario_selecionado]
                
                with st.form("form_edit_colab"):
                    col1, col2 = st.columns(2)
                    with col1:
                        edit_nome = st.text_input("Nome Completo", value=user_data.get('nome', ''))
                        edit_email = st.text_input("E-mail", value=user_data.get('email', f"{usuario_selecionado}@weg.net"))
                        edit_area = st.text_input("Área / Setor", value=user_data.get('area', ''))
                    with col2:
                        roles = ["User", "Facilitador", "Admin"]
                        current_role = user_data.get('role', 'User')
                        role_index = roles.index(current_role) if current_role in roles else 0
                        
                        edit_papel = st.selectbox("Nível de Acesso", roles, index=role_index)
                        edit_ativo = st.checkbox("Colaborador Ativo (Acesso Liberado)", value=user_data.get('ativo', True))
                    
                    st.info("Nota: A senha do usuário não pode ser alterada aqui. Caso ele esqueça, peça para usar a aba 'Esqueci a Senha' no login.")
                    
                    btn_edit = st.form_submit_button("Salvar Alterações")
                    if btn_edit:
                        if usuario_selecionado == st.session_state['current_user']['login'] and (not edit_ativo or edit_papel != "Admin"):
                            st.error("Segurança: Você não pode desativar seu próprio usuário ou remover seu status de Admin.")
                        else:
                            st.session_state['db_users'][usuario_selecionado].update({
                                "nome": edit_nome,
                                "email": edit_email,
                                "area": edit_area,
                                "role": edit_papel,
                                "ativo": edit_ativo
                            })
                            st.success(f"Dados de '{usuario_selecionado}' atualizados com sucesso! Atualize a página.")

def pagina_administracao():
    st.header("⚙️ Painel de Administração")
    
    if st.session_state['current_user']['role'] != 'Admin':
        st.error("Acesso restrito: Somente administradores podem acessar esta página.")
        return
        
    st.markdown("Bem-vindo ao painel de gestão de acessos e configurações.")
    
    st.subheader("📝 Solicitações de Acesso (Pendentes)")
    pendentes = [req for req in st.session_state['db_requests'] if req['status'] == 'pendente']
    
    if not pendentes:
        st.success("Nenhuma solicitação de acesso pendente no momento.")
    else:
        for req in pendentes:
            with st.expander(f"📌 {req['nome']} - {req['email']}", expanded=True):
                st.write(f"**Data da solicitação:** {req['data']}")
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    if st.button("✅ Aprovar", key=f"apr_{req['id']}", type="primary"):
                        aprovar_solicitacao(req['id'])
                        st.success(f"Aprovado! Vá em 'Colaboradores' para editar a área se desejar.")
                        st.rerun()
                with col2:
                    if st.button("❌ Rejeitar", key=f"rej_{req['id']}"):
                        rejeitar_solicitacao(req['id'])
                        st.warning(f"Rejeitado! Atualize a página.")
                        st.rerun()
                        
    st.markdown("---")
    
    st.subheader("📜 Histórico de Solicitações")
    historico = [req for req in st.session_state['db_requests'] if req['status'] != 'pendente']
    
    if historico:
        df_hist = pd.DataFrame(historico)
        df_hist = df_hist[['nome', 'email', 'status', 'data']]
        df_hist.columns = ['Nome', 'E-mail', 'Status', 'Data']
        
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
