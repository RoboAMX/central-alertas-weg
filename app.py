import streamlit as st
import datetime
import pandas as pd
from supabase import create_client, Client

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
# 2. CONEXÃO COM BANCO DE DADOS (SUPABASE)
# ==========================================
@st.cache_resource
def init_connection() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

try:
    supabase = init_connection()
except Exception as e:
    st.error("⚠️ Erro de conexão com o Banco de Dados. Verifique as configurações (Secrets).")
    st.stop()

# Controle de Sessão Atual
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False
if 'must_change_password' not in st.session_state:
    st.session_state['must_change_password'] = False
if 'current_user' not in st.session_state:
    st.session_state['current_user'] = None

# ==========================================
# 3. FUNÇÕES DE AUTENTICAÇÃO E BD
# ==========================================
def fazer_login(usuario_login, senha):
    usuario_login = usuario_login.strip().lower() 
    
    # Busca o usuário no Banco de Dados
    resposta = supabase.table("usuarios").select("*").eq("login", usuario_login).execute()
    
    if len(resposta.data) > 0:
        usuario = resposta.data[0]
        if usuario.get('ativo', True) and usuario.get('senha') == senha:
            st.session_state['authenticated'] = True
            st.session_state['current_user'] = {
                "login": usuario['login'],
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

def aprovar_solicitacao(req_id, req_email, req_nome):
    # 1. Atualiza status no banco
    supabase.table("solicitacoes").update({"status": "aprovado"}).eq("id", req_id).execute()
    
    # 2. Cria o novo usuário no banco
    login_extraido = req_email.strip().lower().split('@')[0]
    
    # Verifica se já existe para não dar erro
    check = supabase.table("usuarios").select("login").eq("login", login_extraido).execute()
    if len(check.data) == 0:
        supabase.table("usuarios").insert({
            "login": login_extraido,
            "nome": req_nome,
            "email": req_email,
            "senha": "WEG2026",
            "area": "A definir",
            "role": "User",
            "ativo": True
        }).execute()

def rejeitar_solicitacao(req_id):
    supabase.table("solicitacoes").update({"status": "rejeitado"}).eq("id", req_id).execute()

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
                        # Grava no banco de dados real
                        supabase.table("solicitacoes").insert({
                            "nome": req_nome,
                            "email": req_email,
                            "status": "pendente",
                            "data": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                        }).execute()
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
                    check = supabase.table("usuarios").select("login").eq("login", user_clean).execute()
                    if len(check.data) > 0:
                        supabase.table("usuarios").update({"senha": "WEG2026"}).eq("login", user_clean).execute()
                        st.success(f"✅ Senha redefinida para **WEG2026**.")
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
                    # Atualiza a senha no banco real
                    supabase.table("usuarios").update({"senha": nova_senha}).eq("login", login_atual).execute()
                    
                    st.session_state['must_change_password'] = False
                    st.success("Senha alterada com sucesso!")
                    st.rerun()

# ==========================================
# 5. COMPONENTES DE LAYOUT
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
    st.info("Visão geral dos alertas, problemas e KPIs.")

def pagina_problemas():
    st.header("Gestão de Problemas")
    st.info("Abertura e listagem de problemas.")

def pagina_acoes():
    st.header("Minhas Ações Corretivas")
    st.info("Lista de ações onde você é o responsável.")

def pagina_colaboradores():
    st.header("👥 Gestão de Colaboradores")
    
    is_admin = st.session_state['current_user']['role'] == 'Admin'
    
    if is_admin:
        tab1, tab2, tab3 = st.tabs(["📋 Lista de Colaboradores", "➕ Adicionar Novo", "✏️ Editar / Desativar"])
    else:
        tab1, = st.tabs(["📋 Lista de Colaboradores"])
    
    # Busca usuários reais do banco
    users_db = supabase.table("usuarios").select("*").execute().data
    
    with tab1:
        if users_db:
            df_users = pd.DataFrame(users_db)
            df_display = df_users[['login', 'nome', 'email', 'area', 'role', 'ativo']].copy()
            df_display.columns = ['Usuário', 'Nome Completo', 'E-mail', 'Área / Setor', 'Papel', 'Status Ativo']
            
            def colorir_ativo(val):
                if isinstance(val, bool):
                    color = 'green' if val else 'red'
                    return f'color: {color}; font-weight: bold;'
                return ''
            
            try:
                tabela_estilizada = df_display.style.map(colorir_ativo, subset=['Status Ativo'])
            except AttributeError:
                tabela_estilizada = df_display.style.applymap(colorir_ativo, subset=['Status Ativo'])
                
            st.dataframe(tabela_estilizada, use_container_width=True, hide_index=True)
        else:
            st.warning("Nenhum usuário encontrado.")

    if is_admin:
        with tab2:
            st.markdown("Adicione um colaborador manualmente ao sistema.")
            with st.form("form_add_colab"):
                col1, col2 = st.columns(2)
                with col1:
                    novo_nome = st.text_input("Nome Completo*")
                    novo_email = st.text_input("E-mail (@weg.net)*")
                with col2:
                    novo_area = st.text_input("Área / Setor*")
                    novo_papel = st.selectbox("Nível de Acesso*", ["User", "Facilitador", "Admin"])
                
                if st.form_submit_button("Salvar Colaborador"):
                    if novo_nome and novo_email and novo_area:
                        novo_login = novo_email.strip().lower().split('@')[0]
                        check = supabase.table("usuarios").select("login").eq("login", novo_login).execute()
                        if len(check.data) > 0:
                            st.error(f"O usuário '{novo_login}' já existe no BD!")
                        else:
                            supabase.table("usuarios").insert({
                                "login": novo_login,
                                "nome": novo_nome,
                                "email": novo_email,
                                "senha": "WEG2026",
                                "area": novo_area,
                                "role": novo_papel,
                                "ativo": True
                            }).execute()
                            st.success("Colaborador adicionado com sucesso!")
                    else:
                        st.warning("Preencha todos os campos obrigatórios.")
                        
        with tab3:
            logins = [u['login'] for u in users_db]
            usuario_selecionado = st.selectbox("Selecione o Usuário:", logins)
            
            if usuario_selecionado:
                user_data = next((u for u in users_db if u['login'] == usuario_selecionado), None)
                if user_data:
                    with st.form("form_edit_colab"):
                        col1, col2 = st.columns(2)
                        with col1:
                            edit_nome = st.text_input("Nome", value=user_data['nome'])
                            edit_email = st.text_input("E-mail", value=user_data['email'])
                            edit_area = st.text_input("Área", value=user_data['area'])
                        with col2:
                            roles = ["User", "Facilitador", "Admin"]
                            role_index = roles.index(user_data['role']) if user_data['role'] in roles else 0
                            edit_papel = st.selectbox("Nível de Acesso", roles, index=role_index)
                            edit_ativo = st.checkbox("Colaborador Ativo", value=user_data['ativo'])
                        
                        if st.form_submit_button("Salvar Alterações"):
                            if usuario_selecionado == st.session_state['current_user']['login'] and (not edit_ativo or edit_papel != "Admin"):
                                st.error("Segurança: Você não pode remover seu próprio acesso.")
                            else:
                                supabase.table("usuarios").update({
                                    "nome": edit_nome,
                                    "email": edit_email,
                                    "area": edit_area,
                                    "role": edit_papel,
                                    "ativo": edit_ativo
                                }).eq("login", usuario_selecionado).execute()
                                st.success("Atualizado com sucesso!")

def pagina_administracao():
    st.header("⚙️ Painel de Administração")
    
    if st.session_state['current_user']['role'] != 'Admin':
        st.error("Acesso restrito.")
        return
        
    st.subheader("📝 Solicitações de Acesso (Pendentes)")
    
    reqs_db = supabase.table("solicitacoes").select("*").execute().data
    pendentes = [r for r in reqs_db if r['status'] == 'pendente']
    
    if not pendentes:
        st.success("Nenhuma solicitação de acesso pendente.")
    else:
        for req in pendentes:
            with st.expander(f"📌 {req['nome']} - {req['email']}", expanded=True):
                st.write(f"Data: {req['data']}")
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    if st.button("✅ Aprovar", key=f"apr_{req['id']}", type="primary"):
                        aprovar_solicitacao(req['id'], req['email'], req['nome'])
                        st.success("Aprovado! Atualize a página.")
                        st.rerun()
                with col2:
                    if st.button("❌ Rejeitar", key=f"rej_{req['id']}"):
                        rejeitar_solicitacao(req['id'])
                        st.warning("Rejeitado! Atualize a página.")
                        st.rerun()
                        
    st.markdown("---")
    st.subheader("📜 Histórico de Solicitações")
    historico = [r for r in reqs_db if r['status'] != 'pendente']
    
    if historico:
        df_hist = pd.DataFrame(historico)[['nome', 'email', 'status', 'data']]
        df_hist.columns = ['Nome', 'E-mail', 'Status', 'Data']
        def colorir_status(val):
            return f"color: {'green' if val == 'aprovado' else 'red'}; font-weight: bold;"
        try:
            st.dataframe(df_hist.style.map(colorir_status, subset=['Status']), use_container_width=True, hide_index=True)
        except:
            st.dataframe(df_hist.style.applymap(colorir_status, subset=['Status']), use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum histórico.")

# ==========================================
# 7. ROTEADOR
# ==========================================
def main():
    if not st.session_state['authenticated']:
        render_login()
    elif st.session_state['must_change_password']:
        render_trocar_senha()
    else:
        render_header()
        pagina_atual = render_sidebar()
        if "Dashboard" in pagina_atual: pagina_dashboard()
        elif "Problemas" in pagina_atual: pagina_problemas()
        elif "Ações" in pagina_atual: pagina_acoes()
        elif "Colaboradores" in pagina_atual: pagina_colaboradores()
        elif "Administração" in pagina_atual: pagina_administracao()

if __name__ == "__main__":
    main()
