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
# 2. CONEXÃO COM BANCO DE DADOS E MEMÓRIA
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

# Inicialização de Variáveis de Sessão Seguras
if 'authenticated' not in st.session_state: st.session_state['authenticated'] = False
if 'must_change_password' not in st.session_state: st.session_state['must_change_password'] = False
if 'current_user' not in st.session_state: st.session_state['current_user'] = None
if 'menu_index' not in st.session_state: st.session_state['menu_index'] = 0
if 'notif_count' not in st.session_state: st.session_state['notif_count'] = 0

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
                "login": usuario['login'], "nome": usuario['nome'],
                "area": usuario['area'], "role": usuario['role']
            }
            if senha == "WEG2026": st.session_state['must_change_password'] = True
            else: st.session_state['must_change_password'] = False
            return True
    return False

def fazer_logout():
    st.session_state['authenticated'] = False
    st.session_state['must_change_password'] = False
    st.session_state['current_user'] = None
    st.session_state['menu_index'] = 0
    st.rerun()

def aprovar_solicitacao(req_id, req_email, req_nome):
    supabase.table("solicitacoes").update({"status": "aprovado"}).eq("id", req_id).execute()
    login_extraido = req_email.strip().lower().split('@')[0]
    check = supabase.table("usuarios").select("login").eq("login", login_extraido).execute()
    if len(check.data) == 0:
        supabase.table("usuarios").insert({
            "login": login_extraido, "nome": req_nome, "email": req_email,
            "senha": "WEG2026", "area": "A definir", "role": "User", "ativo": True
        }).execute()

def rejeitar_solicitacao(req_id):
    supabase.table("solicitacoes").update({"status": "rejeitado"}).eq("id", req_id).execute()

# Função auxiliar para enviar notificação (AGORA COM LINK)
def enviar_notificacao(user_login, titulo, corpo, link=""):
    try:
        supabase.table("notifications").insert({
            "user_login": user_login,
            "titulo": titulo,
            "corpo": corpo,
            "link": link,
            "lida": False
        }).execute()
    except: pass

# ==========================================
# 4. TELAS DE LOGIN E RESET
# ==========================================
def render_login():
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.write("<br><br>", unsafe_allow_html=True)
        try: st.image("logo_weg.png", width=200)
        except: st.markdown("### [LOGO WEG]")
        st.markdown("<h2 style='color: #00579D;'>Central de Alertas</h2>", unsafe_allow_html=True)
        aba_login, aba_solicitar, aba_reset = st.tabs(["🔐 Entrar", "📝 Solicitar Acesso", "🔑 Esqueci a Senha"])
        
        with aba_login:
            with st.form("form_login"):
                usuario_login = st.text_input("Usuário WEG")
                senha = st.text_input("Senha", type="password")
                if st.form_submit_button("Entrar", use_container_width=True):
                    if fazer_login(usuario_login, senha): st.rerun()
                    else: st.error("Usuário ou senha incorretos, ou cadastro inativo.")
        
        with aba_solicitar:
            with st.form("form_solicitacao"):
                req_nome = st.text_input("Nome Completo")
                req_email = st.text_input("E-mail corporativo (@weg.net)")
                if st.form_submit_button("Enviar Solicitação", use_container_width=True):
                    if req_nome and req_email:
                        supabase.table("solicitacoes").insert({"nome": req_nome, "email": req_email, "status": "pendente", "data": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}).execute()
                        st.success("Solicitação enviada! Aguarde a aprovação.")
                    else: st.warning("Preencha todos os campos obrigatórios.")
                        
        with aba_reset:
            st.info("Informe seu usuário para redefinir a senha.")
            with st.form("form_reset"):
                reset_usuario = st.text_input("Usuário WEG")
                if st.form_submit_button("Redefinir Senha", use_container_width=True):
                    user_clean = reset_usuario.strip().lower()
                    check = supabase.table("usuarios").select("login").eq("login", user_clean).execute()
                    if len(check.data) > 0:
                        supabase.table("usuarios").update({"senha": "WEG2026"}).eq("login", user_clean).execute()
                        st.success("✅ Senha redefinida para **WEG2026**.")
                    else: st.error("Usuário não encontrado.")

def render_trocar_senha():
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.write("<br><br>", unsafe_allow_html=True)
        st.warning("⚠️ Troca de Senha Obrigatória")
        with st.form("form_troca_senha"):
            nova_senha = st.text_input("Nova Senha", type="password")
            confirma_senha = st.text_input("Confirmar Nova Senha", type="password")
            if st.form_submit_button("Salvar e Continuar", use_container_width=True):
                if len(nova_senha) < 6: st.error("A nova senha deve ter pelo menos 6 caracteres.")
                elif nova_senha == "WEG2026": st.error("A nova senha não pode ser igual à padrão.")
                elif nova_senha != confirma_senha: st.error("As senhas não coincidem.")
                else:
                    login_atual = st.session_state['current_user']['login']
                    supabase.table("usuarios").update({"senha": nova_senha}).eq("login", login_atual).execute()
                    st.session_state['must_change_password'] = False
                    st.success("Senha alterada com sucesso!")
                    st.rerun()

# ==========================================
# 5. COMPONENTES DE LAYOUT (SINO E PUSH IN-APP)
# ==========================================
def render_header():
    col1, col2, col3 = st.columns([7, 2, 2])
    with col1: st.title("Central de Alertas")
        
    with col2: 
        try:
            notifs = supabase.table("notifications").select("*").eq("user_login", st.session_state['current_user']['login']).eq("lida", False).order("id", desc=True).execute().data
            qtd = len(notifs)
        except:
            notifs = []; qtd = 0
            
        # PUSH NOTIFICATION (TOAST DO STREAMLIT)
        if qtd > st.session_state['notif_count']:
            st.toast("Você tem novas notificações!", icon="🔔")
        st.session_state['notif_count'] = qtd
            
        cor_sino = "🔴" if qtd > 0 else "⚪"
        texto_sino = f"🔔 {qtd} Novas" if qtd > 0 else "🔔 Nenhuma"
        
        st.write("<br>", unsafe_allow_html=True)
        with st.popover(texto_sino, use_container_width=True):
            st.markdown(f"**Suas Notificações {cor_sino}**")
            if qtd == 0: st.info("Tudo limpo por aqui!")
            else:
                for n in notifs:
                    st.warning(f"**{n['titulo']}**\n\n{n['corpo']}")
                    
                    # Roteador Interno via Notificação
                    txt_btn = f"Ler e ir para {n['link']}" if n['link'] else "Marcar como Lida"
                    if st.button(txt_btn, key=f"read_{n['id']}", type="primary"):
                        supabase.table("notifications").update({"lida": True}).eq("id", n['id']).execute()
                        
                        # Muda a aba lateral automaticamente
                        if n['link'] == "Problemas": st.session_state['menu_index'] = 1
                        elif n['link'] == "Minhas Ações": st.session_state['menu_index'] = 2
                        st.rerun()
                        
    with col3: 
        st.write("<br>", unsafe_allow_html=True)
        st.markdown(f"**👤 {st.session_state['current_user']['nome']}**<br><span style='font-size:12px; color:gray;'>{st.session_state['current_user']['area']}</span>", unsafe_allow_html=True)
    st.markdown("---")

def render_sidebar():
    try: st.sidebar.image("logo_weg.png", width=150)
    except: st.sidebar.markdown("**[LOGO WEG]**")
    st.sidebar.markdown("### 🚨 Navegação")
    
    opcoes_menu = ["📊 Dashboard", "⚠️ Problemas", "✅ Minhas Ações", "👥 Colaboradores", "⚙️ Administração"]
    
    # Callback para manter a navegação sincronizada (Resolve o Erro de Widget Key)
    def update_menu():
        st.session_state['menu_index'] = opcoes_menu.index(st.session_state['_menu_radio'])
        
    menu_selecionado = st.sidebar.radio(
        "Selecione a página:", 
        opcoes_menu, 
        index=st.session_state['menu_index'], 
        key='_menu_radio',
        on_change=update_menu
    )
    
    st.sidebar.markdown("---")
    st.sidebar.caption(f"Logado como: **{st.session_state['current_user']['role']}**")
    if st.sidebar.button("Sair (Logout)", use_container_width=True): fazer_logout()
    return menu_selecionado

# ==========================================
# 6. PÁGINAS DO SISTEMA
# ==========================================
def pagina_dashboard():
    st.header("📊 Dashboard")
    st.info("Visão geral dos alertas, problemas e KPIs. (Step 11)")

def pagina_problemas():
    st.header("⚠️ Gestão de Problemas e Alertas")
    users_db = supabase.table("usuarios").select("*").execute().data
    areas = list(set([u['area'] for u in users_db if u['area'] and u['area'] != 'A definir']))
    areas.sort()
    if not areas: areas = ["Geral"]

    tab_lista, tab_novo, tab_detalhe = st.tabs(["📋 Listagem de Alertas", "➕ Abrir Novo Alerta", "🔍 Detalhes do Alerta"])
    
    with tab_lista:
        colF1, colF2, colF3 = st.columns(3)
        with colF1: filtro_status = st.selectbox("Status", ["Todos", "aberto", "em_analise", "aprovado", "rejeitado", "solucionado"])
        with colF2: filtro_prio = st.selectbox("Prioridade", ["Todas", "Urgente", "Normal", "Baixo"])
            
        try:
            problemas_db = supabase.table("problemas").select("*").order("id", desc=True).execute().data
            if problemas_db:
                df_prob = pd.DataFrame(problemas_db)
                if filtro_status != "Todos": df_prob = df_prob[df_prob['status'] == filtro_status]
                if filtro_prio != "Todas": df_prob = df_prob[df_prob['prioridade'] == filtro_prio]
                    
                if not df_prob.empty:
                    df_display = df_prob[['id', 'titulo', 'area', 'prioridade', 'status', 'criado_em', 'sla_due_at']].copy()
                    st.dataframe(df_display, use_container_width=True, hide_index=True)
                else: st.info("Nenhum alerta encontrado.")
            else: st.info("Nenhum problema cadastrado.")
        except Exception as e: st.error(f"Erro: {str(e)}")

    with tab_novo:
        with st.form("form_novo_prob"):
            titulo = st.text_input("Título do Alerta / Problema*")
            descricao = st.text_area("Descrição detalhada*")
            col1, col2 = st.columns(2)
            with col1: area_prob = st.selectbox("Área afetada*", areas)
            with col2: prioridade = st.selectbox("Prioridade*", ["Urgente", "Normal", "Baixo"])
            
            if st.form_submit_button("Abrir Alerta", type="primary"):
                if titulo and descricao:
                    dias_sla = {"Urgente": 1, "Normal": 3, "Baixo": 5}
                    prazo = datetime.datetime.now() + datetime.timedelta(days=dias_sla[prioridade])
                    try:
                        supabase.table("problemas").insert({
                            "titulo": titulo, "descricao": descricao, "area": area_prob,
                            "prioridade": prioridade, "status": "aberto",
                            "criado_por": st.session_state['current_user']['login'],
                            "criado_em": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "sla_due_at": prazo.strftime("%Y-%m-%d %H:%M:%S")
                        }).execute()
                        st.success("✅ Alerta registrado com sucesso!")
                        st.rerun()
                    except Exception as e: st.warning(f"Erro: {str(e)}")
                else: st.warning("Título e Descrição obrigatórios.")

    with tab_detalhe:
        try:
            problemas_db = supabase.table("problemas").select("*").order("id", desc=True).execute().data
            if problemas_db:
                opcoes_ids = [str(p['id']) + f" - {p['titulo']}" for p in problemas_db]
                id_selecionado = st.selectbox("Selecione o Alerta:", [""] + opcoes_ids)
                
                if id_selecionado != "":
                    id_real = int(id_selecionado.split(" - ")[0])
                    alerta = next((p for p in problemas_db if p['id'] == id_real), None)
                    
                    if alerta:
                        st.markdown(f"### #{alerta['id']} - {alerta['titulo']}")
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Área", alerta['area'])
                        c2.metric("Prioridade", alerta['prioridade'])
                        c3.metric("Status", alerta['status'].upper())
                        st.info(alerta['descricao'])
                        st.markdown("---")
                        
                        if alerta['status'] == 'aberto':
                            st.markdown("### ⚙️ Análise do Facilitador")
                            is_admin = st.session_state['current_user']['role'] == 'Admin'
                            is_creator = st.session_state['current_user']['login'] == alerta['criado_por']
                            fac_resp = supabase.table("area_facilitadores").select("facilitador_login").eq("area", alerta['area']).execute()
                            fac_area = fac_resp.data[0]['facilitador_login'] if fac_resp.data else None
                            is_facilitator = st.session_state['current_user']['login'] == fac_area
                            
                            if is_creator and not is_admin: st.warning("⚠️ Bloqueado: Você não pode aprovar um alerta criado por você mesmo.")
                            elif not is_admin and not is_facilitator: st.warning("⚠️ Apenas o Admin ou Facilitador podem aprovar.")
                            else:
                                c_apr, c_rej = st.columns(2)
                                with c_apr:
                                    if st.button("✅ Aprovar Alerta", use_container_width=True, type="primary"):
                                        supabase.table("problemas").update({"status": "aprovado"}).eq("id", alerta['id']).execute()
                                        st.success("Aprovado!"); st.rerun()
                                with c_rej:
                                    with st.popover("❌ Rejeitar", use_container_width=True):
                                        motivo = st.text_area("Motivo da Rejeição*")
                                        if st.button("Confirmar Rejeição") and motivo:
                                            supabase.table("problemas").update({"status": "rejeitado"}).eq("id", alerta['id']).execute()
                                            supabase.table("problem_justifications").insert({"problem_id": alerta['id'], "autor": st.session_state['current_user']['login'], "acao": "rejeitado", "motivo": motivo}).execute()
                                            enviar_notificacao(alerta['criado_por'], f"Alerta #{alerta['id']} Rejeitado", f"Motivo: {motivo}", "Problemas")
                                            st.rerun()
                        
                        elif alerta['status'] == 'rejeitado':
                            just_db = supabase.table("problem_justifications").select("*").eq("problem_id", alerta['id']).eq("acao", "rejeitado").execute().data
                            st.error(f"🚨 **ALERTA REJEITADO**\n\n**Motivo:** {just_db[-1]['motivo'] if just_db else ''}")
                            
                        elif alerta['status'] in ['aprovado', 'solucionado']:
                            st.markdown("### ✅ Plano de Ações Corretivas")
                            acoes_db = supabase.table("problem_actions").select("*").eq("problem_id", alerta['id']).execute().data
                            
                            if acoes_db:
                                for acao in acoes_db:
                                    with st.expander(f"Ação: {acao['descricao']} | Status: {acao['status'].upper()}", expanded=True):
                                        resp_db = supabase.table("problem_action_responsibles").select("colaborador_login").eq("action_id", acao['id']).execute().data
                                        logins_resp = [r['colaborador_login'] for r in resp_db]
                                        st.write(f"**Responsáveis:** {', '.join([u['nome'] for u in users_db if u['login'] in logins_resp])}")
                                        
                                        if st.session_state['current_user']['role'] == 'Admin' or st.session_state['current_user']['login'] in logins_resp:
                                            with st.form(f"form_acao_{acao['id']}"):
                                                novo_status = st.selectbox("Status", ["pendente", "em_andamento", "solucionado"], index=["pendente", "em_andamento", "solucionado"].index(acao['status']))
                                                nova_obs = st.text_area("Observações", value=acao['observacao'] if acao['observacao'] else "")
                                                if st.form_submit_button("Atualizar Ação"):
                                                    supabase.table("problem_actions").update({"status": novo_status, "observacao": nova_obs}).eq("id", acao['id']).execute()
                                                    if novo_status == 'solucionado' and acao['status'] != 'solucionado':
                                                        enviar_notificacao(alerta['criado_por'], "Ação Concluída ✅", f"Ação '{acao['descricao']}' (Alerta #{alerta['id']}) finalizada!", "Problemas")
                                                    st.rerun()
                                        else: st.write(f"**Observações:** {acao['observacao']}")

                            st.markdown("#### Adicionar Nova Ação")
                            with st.form("form_nova_acao"):
                                desc_acao = st.text_input("O que deve ser feito?")
                                prazo_acao = st.date_input("Prazo final")
                                options_usr = {u['login']: f"{u['nome']}" for u in users_db if u['ativo']}
                                selecionados = st.multiselect("Responsáveis", list(options_usr.keys()), format_func=lambda x: options_usr[x])
                                
                                if st.form_submit_button("Salvar Ação") and desc_acao and selecionados:
                                    res = supabase.table("problem_actions").insert({"problem_id": alerta['id'], "descricao": desc_acao, "status": "pendente", "prazo": str(prazo_acao), "criado_por": st.session_state['current_user']['login']}).execute()
                                    action_id = res.data[0]['id']
                                    for resp_log in selecionados:
                                        supabase.table("problem_action_responsibles").insert({"action_id": action_id, "colaborador_login": resp_log}).execute()
                                        enviar_notificacao(resp_log, "Nova Ação Atribuída 📋", f"Você deve resolver: '{desc_acao}' (Alerta #{alerta['id']})", "Minhas Ações")
                                    st.success("Criado!"); st.rerun()
        except: pass

def pagina_acoes():
    st.header("✅ Minhas Ações Corretivas")
    st.markdown("Ações em que você foi designado como responsável.")
    try:
        meu_login = st.session_state['current_user']['login']
        resp_db = supabase.table("problem_action_responsibles").select("action_id").eq("colaborador_login", meu_login).execute().data
        if not resp_db: st.success("🎉 Você não possui nenhuma ação pendente no momento!")
        else:
            action_ids = [r['action_id'] for r in resp_db]
            acoes_db = supabase.table("problem_actions").select("*").in_("id", action_ids).execute().data
            if acoes_db:
                df_acoes = pd.DataFrame(acoes_db)
                prob_ids = df_acoes['problem_id'].unique().tolist()
                probs_db = supabase.table("problemas").select("id, titulo").in_("id", prob_ids).execute().data
                df_acoes['Alerta_Origem'] = df_acoes['problem_id'].map({p['id']: p['titulo'] for p in probs_db})
                df_display = df_acoes[['id', 'Alerta_Origem', 'descricao', 'prazo', 'status']].copy()
                df_display.columns = ['ID Ação', 'Alerta Origem', 'O que fazer', 'Prazo', 'Status']
                
                def color_status(val):
                    return 'color: green;' if val == 'solucionado' else 'color: red;' if val == 'pendente' else 'color: orange;'
                try: st.dataframe(df_display.style.map(color_status, subset=['Status']), use_container_width=True, hide_index=True)
                except: st.dataframe(df_display.style.applymap(color_status, subset=['Status']), use_container_width=True, hide_index=True)
                st.info("💡 Para atualizar, vá no Menu 'Problemas' -> Aba 'Detalhes'.")
    except: pass

def pagina_colaboradores():
    st.header("👥 Gestão de Colaboradores")
    tab1, = st.tabs(["📋 Lista de Colaboradores"])
    users_db = supabase.table("usuarios").select("*").execute().data
    if users_db:
        df_users = pd.DataFrame(users_db)
        df_display = df_users[['login', 'nome', 'email', 'area', 'role', 'ativo']].copy()
        df_display.columns = ['Usuário', 'Nome', 'E-mail', 'Área', 'Papel', 'Ativo']
        try: st.dataframe(df_display.style.map(lambda v: f"color: {'green' if v else 'red'}", subset=['Ativo']), use_container_width=True, hide_index=True)
        except: st.dataframe(df_display.style.applymap(lambda v: f"color: {'green' if v else 'red'}", subset=['Ativo']), use_container_width=True, hide_index=True)

def pagina_administracao():
    st.header("⚙️ Painel de Administração")
    if st.session_state['current_user']['role'] != 'Admin': st.error("Acesso restrito."); return
    users_db = supabase.table("usuarios").select("*").execute().data
    colA, colB = st.columns([1, 1])
    with colA:
        st.subheader("👨‍💼 Facilitadores")
        areas = sorted(list(set([u['area'] for u in users_db if u['area'] and u['area'] != 'A definir'])))
        if areas:
            fac_map = {f['area']: f['facilitador_login'] for f in supabase.table("area_facilitadores").select("*").execute().data}
            with st.form("form_facilitadores"):
                area_selecionada = st.selectbox("Área", areas)
                user_options = ["Nenhum"] + [f"{u['nome']} ({u['login']})" for u in users_db if u['ativo']]
                idx = 0
                if fac_map.get(area_selecionada):
                    for i, opt in enumerate(user_options):
                        if f"({fac_map.get(area_selecionada)})" in opt: idx = i; break
                novo_fac = st.selectbox("Facilitador", user_options, index=idx)
                if st.form_submit_button("Salvar"):
                    if novo_fac == "Nenhum": supabase.table("area_facilitadores").delete().eq("area", area_selecionada).execute()
                    else:
                        fac_log = novo_fac.split("(")[-1].replace(")", "")
                        supabase.table("area_facilitadores").upsert({"area": area_selecionada, "facilitador_login": fac_log}).execute()
                    st.rerun()
    with colB:
        st.subheader("📝 Solicitações Pendentes")
        pendentes = [r for r in supabase.table("solicitacoes").select("*").execute().data if r['status'] == 'pendente']
        if pendentes:
            for req in pendentes:
                with st.expander(f"📌 {req['nome']}", expanded=True):
                    if st.button("✅ Aprovar", key=f"a_{req['id']}"): aprovar_solicitacao(req['id'], req['email'], req['nome']); st.rerun()

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
