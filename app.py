import streamlit as st
import datetime
import pandas as pd
from supabase import create_client, Client

# ==========================================
# 1. CONFIGURAÇÃO DA PÁGINA
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
    st.error("⚠️ Erro de conexão com o Banco de Dados.")
    st.stop()

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
    supabase.table("solicitacoes").update({"status": "aprovado"}).eq("id", req_id).execute()
    login_extraido = req_email.strip().lower().split('@')[0]
    
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
# 4. TELAS DE LOGIN E RESET
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
                        supabase.table("solicitacoes").insert({
                            "nome": req_nome,
                            "email": req_email,
                            "status": "pendente",
                            "data": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                        }).execute()
                        st.success("Solicitação enviada! Aguarde a aprovação.")
                    else:
                        st.warning("Preencha todos os campos obrigatórios.")
                        
        with aba_reset:
            st.info("Informe seu usuário para redefinir a senha.")
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
                        st.error("Usuário não encontrado.")

def render_trocar_senha():
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.write("<br><br>", unsafe_allow_html=True)
        st.warning("⚠️ Troca de Senha Obrigatória")
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
    st.header("📊 Dashboard")
    st.info("Visão geral dos alertas, problemas e KPIs. (Step 11)")

def pagina_problemas():
    st.header("⚠️ Gestão de Problemas e Alertas")
    
    users_db = supabase.table("usuarios").select("area").execute().data
    areas = list(set([u['area'] for u in users_db if u['area'] and u['area'] != 'A definir']))
    areas.sort()
    if not areas:
        areas = ["Geral"]

    tab_lista, tab_novo, tab_detalhe = st.tabs(["📋 Listagem de Alertas", "➕ Abrir Novo Alerta", "🔍 Detalhes"])
    
    # ABA 1: LISTAGEM
    with tab_lista:
        colF1, colF2, colF3 = st.columns(3)
        with colF1:
            filtro_status = st.selectbox("Status", ["Todos", "aberto", "em_analise", "aprovado", "rejeitado", "solucionado"])
        with colF2:
            filtro_prio = st.selectbox("Prioridade", ["Todas", "Urgente", "Normal", "Baixo"])
            
        try:
            problemas_db = supabase.table("problemas").select("*").execute().data
            if problemas_db:
                df_prob = pd.DataFrame(problemas_db)
                if filtro_status != "Todos": df_prob = df_prob[df_prob['status'] == filtro_status]
                if filtro_prio != "Todas": df_prob = df_prob[df_prob['prioridade'] == filtro_prio]
                    
                if not df_prob.empty:
                    df_display = df_prob[['id', 'titulo', 'area', 'prioridade', 'status', 'criado_em', 'sla_due_at']].copy()
                    st.dataframe(df_display, use_container_width=True, hide_index=True)
                    st.caption("Para ver os detalhes, vá na aba 'Detalhes'.")
                else:
                    st.info("Nenhum alerta encontrado com os filtros atuais.")
            else:
                st.info("Nenhum problema cadastrado no sistema ainda.")
        except Exception as e:
            st.error(f"Erro ao carregar lista: {str(e)}")

    # ABA 2: NOVO ALERTA
    with tab_novo:
        st.markdown("Preencha as informações para registrar um novo alerta.")
        with st.form("form_novo_prob"):
            titulo = st.text_input("Título do Alerta / Problema*")
            descricao = st.text_area("Descrição detalhada*")
            
            col1, col2 = st.columns(2)
            with col1:
                area_prob = st.selectbox("Área afetada*", areas)
            with col2:
                prioridade = st.selectbox("Prioridade*", ["Urgente", "Normal", "Baixo"])
                
            anexo = st.file_uploader("Anexar Evidência (Imagem, PDF, Excel)", type=['png','jpg','pdf','xlsx'])
            
            if st.form_submit_button("Abrir Alerta", type="primary"):
                if titulo and descricao:
                    dias_sla = {"Urgente": 1, "Normal": 3, "Baixo": 5}
                    prazo = datetime.datetime.now() + datetime.timedelta(days=dias_sla[prioridade])
                    nome_anexo = anexo.name if anexo else None
                    
                    # TENTATIVA COM TRATAMENTO DE ERROS NA TELA
                    try:
                        supabase.table("problemas").insert({
                            "titulo": titulo,
                            "descricao": descricao,
                            "area": area_prob,
                            "prioridade": prioridade,
                            "status": "aberto",
                            "criado_por": st.session_state['current_user']['login'],
                            "criado_em": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), # Formato puro do Postgres
                            "sla_due_at": prazo.strftime("%Y-%m-%d %H:%M:%S"), # Formato puro do Postgres
                            "anexo": nome_anexo
                        }).execute()
                        
                        st.success("✅ Alerta registrado com sucesso!")
                        st.rerun()
                    except Exception as e:
                        # Se quebrar, ele vai mostrar o erro exato do banco de dados em amarelo
                        st.warning(f"Ocorreu um erro no Banco de Dados: {str(e)}")
                else:
                    st.warning("O Título e a Descrição são obrigatórios.")

    # ABA 3: DETALHES
    with tab_detalhe:
        try:
            problemas_db = supabase.table("problemas").select("*").execute().data
            if not problemas_db:
                st.info("Não há alertas para detalhar.")
            else:
                opcoes_ids = [str(p['id']) + f" - {p['titulo']}" for p in problemas_db]
                id_selecionado = st.selectbox("Selecione o Alerta para ver detalhes:", [""] + opcoes_ids)
                
                if id_selecionado != "":
                    id_real = int(id_selecionado.split(" - ")[0])
                    alerta = next((p for p in problemas_db if p['id'] == id_real), None)
                    
                    if alerta:
                        st.markdown(f"### #{alerta['id']} - {alerta['titulo']}")
                        st.caption(f"Criado por: {alerta['criado_por']} em {alerta['criado_em']}")
                        
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Área", alerta['area'])
                        c2.metric("Prioridade", alerta['prioridade'])
                        c3.metric("Status", alerta['status'].upper())
                        
                        st.markdown("**Descrição:**")
                        st.info(alerta['descricao'])
                        
                        if alerta['anexo']:
                            st.markdown(f"📎 **Anexo:** `{alerta['anexo']}`")
                            
                        st.markdown(f"⏳ **Prazo de Resolução (SLA):** {alerta['sla_due_at']}")
                        st.markdown("---")
                        st.write("*A área de aprovação será habilitada no próximo passo.*")
        except:
            pass

def pagina_acoes():
    st.header("Minhas Ações Corretivas")
    st.info("Lista de ações. (Step 9)")

def pagina_colaboradores():
    st.header("👥 Gestão de Colaboradores")
    is_admin = st.session_state['current_user']['role'] == 'Admin'
    
    if is_admin:
        tab1, tab2, tab3 = st.tabs(["📋 Lista de Colaboradores", "➕ Adicionar Novo", "✏️ Editar / Desativar"])
    else:
        tab1, = st.tabs(["📋 Lista de Colaboradores"])
    
    users_db = supabase.table("usuarios").select("*").execute().data
    
    with tab1:
        if users_db:
            df_users = pd.DataFrame(users_db)
            df_display = df_users[['login', 'nome', 'email', 'area', 'role', 'ativo']].copy()
            df_display.columns = ['Usuário', 'Nome Completo', 'E-mail', 'Área / Setor', 'Papel', 'Status Ativo']
            
            def colorir_ativo(val):
                if isinstance(val, bool):
                    return f"color: {'green' if val else 'red'}; font-weight: bold;"
                return ''
            
            try:
                st.dataframe(df_display.style.map(colorir_ativo, subset=['Status Ativo']), use_container_width=True, hide_index=True)
            except:
                st.dataframe(df_display.style.applymap(colorir_ativo, subset=['Status Ativo']), use_container_width=True, hide_index=True)

    if is_admin:
        with tab2:
            with st.form("form_add_colab"):
                col1, col2 = st.columns(2)
                with col1: novo_nome = st.text_input("Nome*"); novo_email = st.text_input("E-mail*")
                with col2: novo_area = st.text_input("Área*"); novo_papel = st.selectbox("Papel*", ["User", "Facilitador", "Admin"])
                
                if st.form_submit_button("Salvar Colaborador"):
                    if novo_nome and novo_email and novo_area:
                        novo_login = novo_email.strip().lower().split('@')[0]
                        check = supabase.table("usuarios").select("login").eq("login", novo_login).execute()
                        if len(check.data) == 0:
                            supabase.table("usuarios").insert({
                                "login": novo_login, "nome": novo_nome, "email": novo_email,
                                "senha": "WEG2026", "area": novo_area, "role": novo_papel, "ativo": True
                            }).execute()
                            st.success("Adicionado com sucesso!")

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
                            idx = roles.index(user_data['role']) if user_data['role'] in roles else 0
                            edit_papel = st.selectbox("Nível de Acesso", roles, index=idx)
                            edit_ativo = st.checkbox("Ativo", value=user_data['ativo'])
                        
                        if st.form_submit_button("Salvar Alterações"):
                            supabase.table("usuarios").update({
                                "nome": edit_nome, "email": edit_email, "area": edit_area,
                                "role": edit_papel, "ativo": edit_ativo
                            }).eq("login", usuario_selecionado).execute()
                            st.success("Atualizado!")

def pagina_administracao():
    st.header("⚙️ Painel de Administração")
    if st.session_state['current_user']['role'] != 'Admin':
        st.error("Acesso restrito."); return
        
    users_db = supabase.table("usuarios").select("*").execute().data
    colA, colB = st.columns([1, 1])
    
    with colA:
        st.subheader("👨‍💼 Facilitadores por Área")
        areas = list(set([u['area'] for u in users_db if u['area'] and u['area'] != 'A definir']))
        areas.sort()
        if areas:
            fac_db = supabase.table("area_facilitadores").select("*").execute().data
            fac_map = {f['area']: f['facilitador_login'] for f in fac_db}
            with st.form("form_facilitadores"):
                area_selecionada = st.selectbox("1. Selecione a Área", areas)
                active_users = [u for u in users_db if u['ativo']]
                user_options = ["Nenhum"] + [f"{u['nome']} ({u['login']})" for u in active_users]
                
                idx = 0
                current_fac = fac_map.get(area_selecionada, "")
                if current_fac:
                    for i, opt in enumerate(user_options):
                        if f"({current_fac})" in opt: idx = i; break
                            
                novo_fac = st.selectbox("2. Selecione o Facilitador", user_options, index=idx)
                
                if st.form_submit_button("Salvar"):
                    if novo_fac == "Nenhum":
                        supabase.table("area_facilitadores").delete().eq("area", area_selecionada).execute()
                    else:
                        fac_login = novo_fac.split("(")[-1].replace(")", "")
                        supabase.table("area_facilitadores").upsert({"area": area_selecionada, "facilitador_login": fac_login}).execute()
                    st.success("Salvo!")
                    st.rerun()

    with colB:
        st.subheader("📝 Solicitações Pendentes")
        reqs_db = supabase.table("solicitacoes").select("*").execute().data
        pendentes = [r for r in reqs_db if r['status'] == 'pendente']
        if pendentes:
            for req in pendentes:
                with st.expander(f"📌 {req['nome']}", expanded=True):
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("✅ Aprovar", key=f"apr_{req['id']}"):
                            aprovar_solicitacao(req['id'], req['email'], req['nome']); st.rerun()
                    with c2:
                        if st.button("❌ Rejeitar", key=f"rej_{req['id']}"):
                            rejeitar_solicitacao(req['id']); st.rerun()

# ==========================================
# 7. ROTEADOR
# ==========================================
def main():
    if not st.session_state['authenticated']: render_login()
    elif st.session_state['must_change_password']: render_trocar_senha()
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
