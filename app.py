import streamlit as st
import datetime
import pandas as pd
from supabase import create_client, Client
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

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
    st.error("⚠️ Erro de conexão com o Banco de Dados. Verifique os Secrets.")
    st.stop()

if 'authenticated' not in st.session_state: st.session_state['authenticated'] = False
if 'must_change_password' not in st.session_state: st.session_state['must_change_password'] = False
if 'current_user' not in st.session_state: st.session_state['current_user'] = None
if 'menu_index' not in st.session_state: st.session_state['menu_index'] = 0
if 'notif_count' not in st.session_state: st.session_state['notif_count'] = 0

# ==========================================
# 3. FUNÇÕES DE AUTENTICAÇÃO E LÓGICA CORE
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

# --- MOTOR DE E-MAIL E NOTIFICAÇÕES ---
def enviar_email(destinatario, assunto, mensagem_html):
    try:
        remetente = st.secrets.get("EMAIL_SENDER", "")
        senha = st.secrets.get("EMAIL_PASSWORD", "")
        if not remetente or not senha: return
            
        msg = MIMEMultipart()
        msg['From'] = remetente
        msg['To'] = destinatario
        msg['Subject'] = assunto
        
        html_completo = f"""
        <div style="font-family: Arial, sans-serif; color: #333; max-width: 600px; margin: auto; border: 1px solid #ddd; border-radius: 8px; overflow: hidden;">
            <div style="background-color: #00579D; padding: 20px; text-align: center; color: white;">
                <h2 style="margin: 0;">Central de Alertas - WEG</h2>
            </div>
            <div style="padding: 20px; background-color: #f9f9f9;">
                {mensagem_html}
            </div>
            <div style="background-color: #eee; padding: 10px; text-align: center; font-size: 12px; color: #666;">
                Este é um e-mail automático. Por favor, não responda.
            </div>
        </div>
        """
        msg.attach(MIMEText(html_completo, 'html'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(remetente, senha)
        server.send_message(msg)
        server.quit()
    except Exception as e:
        print(f"Erro Email: {e}")

def enviar_notificacao(user_login, titulo, corpo, link=""):
    try:
        supabase.table("notifications").insert({"user_login": user_login, "titulo": titulo, "corpo": corpo, "link": link, "lida": False}).execute()
        resp = supabase.table("usuarios").select("email").eq("login", user_login).execute()
        if len(resp.data) > 0:
            email_destino = resp.data[0]['email']
            html_msg = f"<p>Olá,</p><p>Você tem uma nova notificação no sistema:</p><div style='background-color: white; padding: 15px; border-left: 4px solid #00579D; margin: 20px 0;'><strong>{titulo}</strong><br><br>{corpo}</div><p>Acesse o painel para verificar.</p>"
            enviar_email(email_destino, f"[WEG Alertas] {titulo}", html_msg)
    except: pass

def aprovar_solicitacao_acesso(req_id, req_email, req_nome):
    supabase.table("solicitacoes").update({"status": "aprovado"}).eq("id", req_id).execute()
    login_extraido = req_email.strip().lower().split('@')[0]
    check = supabase.table("usuarios").select("login").eq("login", login_extraido).execute()
    if len(check.data) == 0:
        supabase.table("usuarios").insert({
            "login": login_extraido, "nome": req_nome, "email": req_email,
            "senha": "WEG2026", "area": "A definir", "role": "User", "ativo": True
        }).execute()
        enviar_email(req_email, "Acesso Aprovado", f"Olá {req_nome},<br><br>Seu acesso foi aprovado. Usuário: <b>{login_extraido}</b> | Senha: <b>WEG2026</b>")

def rejeitar_solicitacao_acesso(req_id):
    supabase.table("solicitacoes").update({"status": "rejeitado"}).eq("id", req_id).execute()

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
                        supabase.table("solicitacoes").insert({"nome": req_nome, "email": req_email, "status": "pendente", "data": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}).execute()
                        st.success("Solicitação enviada! Aguarde a aprovação do Administrador.")
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
# 5. COMPONENTES DE LAYOUT
# ==========================================
def render_header():
    col1, col2, col3 = st.columns([7, 2, 2])
    with col1: st.title("Central de Alertas")
        
    with col2: 
        try:
            notifs = supabase.table("notifications").select("*").eq("user_login", st.session_state['current_user']['login']).eq("lida", False).order("id", desc=True).execute().data
            qtd = len(notifs)
        except: notifs = []; qtd = 0
            
        if qtd > st.session_state['notif_count']: st.toast("Você tem novas notificações!", icon="🔔")
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
                    txt_btn = f"Ler e ir para {n['link']}" if n['link'] else "Marcar como Lida"
                    if st.button(txt_btn, key=f"read_{n['id']}", type="primary"):
                        supabase.table("notifications").update({"lida": True}).eq("id", n['id']).execute()
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
    
    def update_menu(): st.session_state['menu_index'] = opcoes_menu.index(st.session_state['_menu_radio'])
    menu_selecionado = st.sidebar.radio("Selecione a página:", opcoes_menu, index=st.session_state['menu_index'], key='_menu_radio', on_change=update_menu)
    
    st.sidebar.markdown("---")
    st.sidebar.caption(f"Logado como: **{st.session_state['current_user']['role']}**")
    if st.sidebar.button("Sair (Logout)", use_container_width=True): fazer_logout()
    return menu_selecionado

# ==========================================
# 6. PÁGINAS DO SISTEMA COMPLETAS
# ==========================================
def pagina_dashboard():
    st.header("📊 Dashboard de Performance")
    
    user_role = st.session_state['current_user']['role']
    user_area = st.session_state['current_user']['area']
    
    # 1. Filtro RLS Lógico (Visão do Dashboard)
    if user_role == 'Admin':
        st.markdown("*Visão Global (Modo Administrador) - Todas as Áreas*")
        probs_data = supabase.table("problemas").select("*").execute().data
    else:
        st.markdown(f"*Visão Filtrada: Sua área ({user_area})*")
        probs_data = supabase.table("problemas").select("*").eq("area", user_area).execute().data
        
    if not probs_data:
        st.info("Nenhum alerta registrado para compor o Dashboard no momento.")
        return

    df = pd.DataFrame(probs_data)
    df['criado_em'] = pd.to_datetime(df['criado_em'])
    df['sla_due_at'] = pd.to_datetime(df['sla_due_at'])
    hoje = datetime.datetime.now()

    # 2. KPIs Base
    abertos = len(df[df['status'] == 'aberto'])
    em_andamento = len(df[df['status'] == 'aprovado'])
    solucionados = len(df[df['status'] == 'solucionado'])
    vencidos = len(df[(df['sla_due_at'] < hoje) & (~df['status'].isin(['solucionado', 'rejeitado']))])

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🚨 Abertos (Aguardando)", abertos)
    col2.metric("⚙️ Em Andamento", em_andamento)
    col3.metric("🔥 Vencidos (SLA)", vencidos, delta="Atenção!" if vencidos > 0 else "No Prazo", delta_color="inverse")
    col4.metric("✅ Solucionados", solucionados)

    st.markdown("---")
    
    colA, colB = st.columns([1, 1])
    
    with colA:
        st.subheader("📈 Alertas por Área")
        df_area = df['area'].value_counts().reset_index()
        df_area.columns = ['Área', 'Quantidade']
        st.bar_chart(df_area.set_index('Área'), color="#00579D")

    with colB:
        st.subheader("🔥 Top Alertas Críticos")
        st.caption("Filtro de alertas não solucionados ordenados por prioridade e vencimento.")
        
        df_criticos = df[~df['status'].isin(['solucionado', 'rejeitado'])].copy()
        if not df_criticos.empty:
            peso_prio = {"Urgente": 1, "Normal": 2, "Baixo": 3}
            df_criticos['peso'] = df_criticos['prioridade'].map(peso_prio)
            df_criticos = df_criticos.sort_values(by=['peso', 'sla_due_at']).head(10)
            
            df_display = df_criticos[['id', 'titulo', 'prioridade', 'status']].copy()
            df_display.columns = ['ID', 'Problema', 'Prioridade', 'Status']
            
            def color_critico(val): return 'color: red; font-weight: bold;' if val == 'Urgente' else ''
            try: st.dataframe(df_display.style.map(color_critico, subset=['Prioridade']), use_container_width=True, hide_index=True)
            except: st.dataframe(df_display.style.applymap(color_critico, subset=['Prioridade']), use_container_width=True, hide_index=True)
        else:
            st.success("Tudo sob controle! Nenhum alerta crítico pendente.")

def pagina_problemas():
    st.header("⚠️ Gestão de Problemas e Alertas")
    users_db = supabase.table("usuarios").select("*").execute().data
    areas = list(set([u['area'] for u in users_db if u['area'] and u['area'] != 'A definir']))
    areas.sort()
    if not areas: areas = ["Geral"]

    # Busca as regras de SLA no banco (Passo 12)
    try: sla_configs = supabase.table("sla_settings").select("*").eq("id", 1).execute().data[0]
    except: sla_configs = {"urgente_dias": 1, "normal_dias": 3, "baixo_dias": 5}

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
                else: st.info("Nenhum alerta encontrado com os filtros selecionados.")
            else: st.info("Nenhum problema cadastrado no sistema.")
        except Exception as e: st.error(f"Erro ao carregar tabela: {str(e)}")

    with tab_novo:
        with st.form("form_novo_prob"):
            titulo = st.text_input("Título do Alerta / Problema*")
            descricao = st.text_area("Descrição detalhada*")
            col1, col2 = st.columns(2)
            with col1: area_prob = st.selectbox("Área afetada*", areas)
            with col2: prioridade = st.selectbox("Prioridade*", ["Urgente", "Normal", "Baixo"])
            anexo = st.file_uploader("Anexar Evidência (Imagem, PDF, Excel)", type=['png','jpg','pdf','xlsx'])
            
            if st.form_submit_button("Abrir Alerta", type="primary"):
                if titulo and descricao:
                    # Aplica o SLA dinâmico do Banco
                    dias_adicionais = sla_configs['urgente_dias'] if prioridade == "Urgente" else sla_configs['normal_dias'] if prioridade == "Normal" else sla_configs['baixo_dias']
                    prazo = datetime.datetime.now() + datetime.timedelta(days=dias_adicionais)
                    nome_anexo = anexo.name if anexo else None
                    
                    try:
                        supabase.table("problemas").insert({
                            "titulo": titulo, "descricao": descricao, "area": area_prob,
                            "prioridade": prioridade, "status": "aberto",
                            "criado_por": st.session_state['current_user']['login'],
                            "criado_em": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "sla_due_at": prazo.strftime("%Y-%m-%d %H:%M:%S"),
                            "anexo": nome_anexo
                        }).execute()
                        st.success("✅ Alerta registrado com sucesso!")
                        st.rerun()
                    except Exception as e: st.error(f"Erro no BD: {str(e)}")
                else: st.warning("Título e Descrição são obrigatórios.")

    with tab_detalhe:
        try:
            problemas_db = supabase.table("problemas").select("*").order("id", desc=True).execute().data
            if problemas_db:
                opcoes_ids = [str(p['id']) + f" - {p['titulo']}" for p in problemas_db]
                id_selecionado = st.selectbox("Selecione o Alerta para ver detalhes:", [""] + opcoes_ids)
                
                if id_selecionado != "":
                    id_real = int(id_selecionado.split(" - ")[0])
                    alerta = next((p for p in problemas_db if p['id'] == id_real), None)
                    
                    if alerta:
                        st.markdown(f"### #{alerta['id']} - {alerta['titulo']}")
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("Área", alerta['area'])
                        c2.metric("Prioridade", alerta['prioridade'])
                        c3.metric("Status", alerta['status'].upper())
                        c4.metric("Vencimento SLA", alerta['sla_due_at'][:10])
                        
                        st.markdown("**Descrição:**")
                        st.info(alerta['descricao'])
                        if alerta['anexo']: st.markdown(f"📎 **Anexo:** `{alerta['anexo']}`")
                        st.markdown("---")
                        
                        # --- ANÁLISE E APROVAÇÃO ---
                        if alerta['status'] == 'aberto':
                            st.markdown("### ⚙️ Análise do Facilitador")
                            is_admin = st.session_state['current_user']['role'] == 'Admin'
                            is_creator = st.session_state['current_user']['login'] == alerta['criado_por']
                            
                            fac_resp = supabase.table("area_facilitadores").select("facilitador_login").eq("area", alerta['area']).execute()
                            fac_area = fac_resp.data[0]['facilitador_login'] if fac_resp.data else None
                            is_facilitator = st.session_state['current_user']['login'] == fac_area
                            
                            if is_creator and not is_admin: st.warning("⚠️ Regra: Você não pode aprovar um alerta criado por você mesmo.")
                            elif not is_admin and not is_facilitator: st.warning("⚠️ Permissão: Apenas o Admin ou o Facilitador da área podem aprovar.")
                            else:
                                c_apr, c_rej = st.columns(2)
                                with c_apr:
                                    if st.button("✅ Aprovar Alerta", use_container_width=True, type="primary"):
                                        supabase.table("problemas").update({"status": "aprovado"}).eq("id", alerta['id']).execute()
                                        supabase.table("problem_justifications").insert({"problem_id": alerta['id'], "autor": st.session_state['current_user']['login'], "acao": "aprovado", "motivo": "Aprovado via painel."}).execute()
                                        enviar_notificacao(alerta['criado_por'], "Alerta Aprovado", f"Seu alerta #{alerta['id']} foi aprovado e agora receberá ações.", "Problemas")
                                        st.success("Aprovado!"); st.rerun()
                                with c_rej:
                                    with st.popover("❌ Rejeitar", use_container_width=True):
                                        motivo = st.text_area("Motivo da Rejeição*")
                                        if st.button("Confirmar Rejeição") and motivo:
                                            supabase.table("problemas").update({"status": "rejeitado"}).eq("id", alerta['id']).execute()
                                            supabase.table("problem_justifications").insert({"problem_id": alerta['id'], "autor": st.session_state['current_user']['login'], "acao": "rejeitado", "motivo": motivo}).execute()
                                            enviar_notificacao(alerta['criado_por'], "Alerta Rejeitado", f"Seu alerta #{alerta['id']} foi rejeitado. Motivo: {motivo}", "Problemas")
                                            st.rerun()
                        
                        elif alerta['status'] == 'rejeitado':
                            just_db = supabase.table("problem_justifications").select("*").eq("problem_id", alerta['id']).eq("acao", "rejeitado").execute().data
                            st.error(f"🚨 **ALERTA REJEITADO (Fechado)**\n\n**Motivo:** {just_db[-1]['motivo'] if just_db else 'Sem motivo registrado.'}")
                            
                        # --- PLANO DE AÇÕES ---
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
                                                nova_obs = st.text_area("Observações da Ação", value=acao['observacao'] if acao['observacao'] else "")
                                                if st.form_submit_button("Atualizar Ação"):
                                                    supabase.table("problem_actions").update({"status": novo_status, "observacao": nova_obs}).eq("id", acao['id']).execute()
                                                    if novo_status == 'solucionado' and acao['status'] != 'solucionado':
                                                        enviar_notificacao(alerta['criado_por'], "Ação Concluída ✅", f"Ação '{acao['descricao']}' finalizada!", "Problemas")
                                                    st.rerun()
                                        else: 
                                            st.info("Apenas responsáveis podem editar.")
                                            st.write(f"**Observações:** {acao['observacao']}")

                            st.markdown("#### Adicionar Nova Ação")
                            with st.form("form_nova_acao"):
                                desc_acao = st.text_input("O que deve ser feito?")
                                prazo_acao = st.date_input("Prazo final")
                                options_usr = {u['login']: f"{u['nome']}" for u in users_db if u['ativo']}
                                selecionados = st.multiselect("Responsáveis", list(options_usr.keys()), format_func=lambda x: options_usr[x])
                                
                                if st.form_submit_button("Salvar Ação"):
                                    if desc_acao and selecionados:
                                        res = supabase.table("problem_actions").insert({"problem_id": alerta['id'], "descricao": desc_acao, "status": "pendente", "prazo": str(prazo_acao), "criado_por": st.session_state['current_user']['login']}).execute()
                                        for resp_log in selecionados:
                                            supabase.table("problem_action_responsibles").insert({"action_id": res.data[0]['id'], "colaborador_login": resp_log}).execute()
                                            enviar_notificacao(resp_log, "Nova Ação Atribuída 📋", f"Você deve resolver: '{desc_acao}'", "Minhas Ações")
                                        st.success("Ação salva!"); st.rerun()
                                    else:
                                        st.error("Preencha descrição e escolha responsáveis.")
        except Exception as e: st.error(f"Erro na exibição dos detalhes: {e}")

def pagina_acoes():
    st.header("✅ Minhas Ações Corretivas")
    st.markdown("Lista completa de ações corretivas em que você foi designado como responsável.")
    try:
        meu_login = st.session_state['current_user']['login']
        resp_db = supabase.table("problem_action_responsibles").select("action_id").eq("colaborador_login", meu_login).execute().data
        if not resp_db: 
            st.success("🎉 Sua caixa está limpa! Nenhuma ação pendente no momento.")
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
                
                def color_st(val): return 'color: green;' if val == 'solucionado' else 'color: red;' if val == 'pendente' else 'color: orange;'
                try: st.dataframe(df_display.style.map(color_st, subset=['Status']), use_container_width=True, hide_index=True)
                except: st.dataframe(df_display.style.applymap(color_st, subset=['Status']), use_container_width=True, hide_index=True)
                st.info("💡 Para alterar status e adicionar comentários, vá ao Menu 'Problemas' e abra o Alerta Origem.")
    except Exception as e: st.error(f"Erro: {e}")

def pagina_colaboradores():
    st.header("👥 Gestão de Colaboradores e Acessos")
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
            def colorir_ativo(val): return f"color: {'green' if val else 'red'}; font-weight: bold;"
            try: st.dataframe(df_display.style.map(colorir_ativo, subset=['Status Ativo']), use_container_width=True, hide_index=True)
            except: st.dataframe(df_display.style.applymap(colorir_ativo, subset=['Status Ativo']), use_container_width=True, hide_index=True)

    if is_admin:
        with tab2:
            st.markdown("Cadastre manualmente um novo colaborador (A senha inicial será WEG2026).")
            with st.form("form_add_colab"):
                col1, col2 = st.columns(2)
                with col1: novo_nome = st.text_input("Nome Completo*"); novo_email = st.text_input("E-mail corporativo*")
                with col2: novo_area = st.text_input("Área / Setor*"); novo_papel = st.selectbox("Papel*", ["User", "Facilitador", "Admin"])
                if st.form_submit_button("Salvar Colaborador"):
                    if novo_nome and novo_email and novo_area:
                        novo_login = novo_email.strip().lower().split('@')[0]
                        check = supabase.table("usuarios").select("login").eq("login", novo_login).execute()
                        if len(check.data) == 0:
                            supabase.table("usuarios").insert({
                                "login": novo_login, "nome": novo_nome, "email": novo_email,
                                "senha": "WEG2026", "area": novo_area, "role": novo_papel, "ativo": True
                            }).execute()
                            st.success("Colaborador adicionado com sucesso!"); st.rerun()
                        else: st.error("O usuário já existe no sistema.")
                    else: st.warning("Preencha todos os campos obrigatórios.")

        with tab3:
            st.markdown("Altere a área, papel ou desative o acesso de um colaborador.")
            logins = [u['login'] for u in users_db]
            usuario_selecionado = st.selectbox("Selecione o Usuário:", logins)
            if usuario_selecionado:
                user_data = next((u for u in users_db if u['login'] == usuario_selecionado), None)
                if user_data:
                    with st.form("form_edit_colab"):
                        col1, col2 = st.columns(2)
                        with col1:
                            edit_nome = st.text_input("Nome Completo", value=user_data['nome'])
                            edit_email = st.text_input("E-mail", value=user_data['email'])
                            edit_area = st.text_input("Área", value=user_data['area'])
                        with col2:
                            roles = ["User", "Facilitador", "Admin"]
                            idx = roles.index(user_data['role']) if user_data['role'] in roles else 0
                            edit_papel = st.selectbox("Nível de Acesso", roles, index=idx)
                            edit_ativo = st.checkbox("Colaborador Ativo (Acesso Liberado)", value=user_data['ativo'])
                        
                        if st.form_submit_button("Salvar Alterações"):
                            if usuario_selecionado == st.session_state['current_user']['login'] and (not edit_ativo or edit_papel != "Admin"):
                                st.error("Regra de Segurança: Você não pode remover seu próprio acesso de Admin ou se desativar.")
                            else:
                                supabase.table("usuarios").update({
                                    "nome": edit_nome, "email": edit_email, "area": edit_area,
                                    "role": edit_papel, "ativo": edit_ativo
                                }).eq("login", usuario_selecionado).execute()
                                st.success("Atualizado com sucesso!"); st.rerun()

def pagina_administracao():
    st.header("⚙️ Painel de Administração e Configurações")
    if st.session_state['current_user']['role'] != 'Admin': 
        st.error("Acesso restrito: Somente administradores podem acessar esta área.")
        return
        
    users_db = supabase.table("usuarios").select("*").execute().data
    colA, colB = st.columns([1, 1])
    
    with colA:
        st.subheader("👨‍💼 Facilitadores por Área")
        st.markdown("Defina os responsáveis pela aprovação de alertas em cada setor.")
        areas = sorted(list(set([u['area'] for u in users_db if u['area'] and u['area'] != 'A definir'])))
        if areas:
            fac_map = {f['area']: f['facilitador_login'] for f in supabase.table("area_facilitadores").select("*").execute().data}
            with st.form("form_facilitadores"):
                area_selecionada = st.selectbox("Selecione a Área", areas)
                user_options = ["Nenhum"] + [f"{u['nome']} ({u['login']})" for u in users_db if u['ativo']]
                idx = 0
                if fac_map.get(area_selecionada):
                    for i, opt in enumerate(user_options):
                        if f"({fac_map.get(area_selecionada)})" in opt: idx = i; break
                novo_fac = st.selectbox("Selecione o Facilitador", user_options, index=idx)
                if st.form_submit_button("Salvar Configuração"):
                    if novo_fac == "Nenhum": supabase.table("area_facilitadores").delete().eq("area", area_selecionada).execute()
                    else:
                        fac_log = novo_fac.split("(")[-1].replace(")", "")
                        supabase.table("area_facilitadores").upsert({"area": area_selecionada, "facilitador_login": fac_log}).execute()
                        usr = next((u for u in users_db if u['login'] == fac_log), None)
                        if usr and usr['role'] == 'User': supabase.table("usuarios").update({"role": "Facilitador"}).eq("login", fac_log).execute()
                    st.success("Facilitador salvo!"); st.rerun()

        st.markdown("---")
        # PASSO 12 - ADMINISTRAÇÃO DE SLA
        st.subheader("⏱️ Configurações de SLA (Prazos)")
        try: sla_configs = supabase.table("sla_settings").select("*").eq("id", 1).execute().data[0]
        except: sla_configs = {"urgente_dias": 1, "normal_dias": 3, "baixo_dias": 5}
        
        with st.form("form_sla"):
            st.markdown("Defina os prazos padrão (em dias corridos) para os Alertas.")
            c1, c2, c3 = st.columns(3)
            with c1: dias_u = st.number_input("Dias (Urgente)", value=sla_configs['urgente_dias'], min_value=1)
            with c2: dias_n = st.number_input("Dias (Normal)", value=sla_configs['normal_dias'], min_value=1)
            with c3: dias_b = st.number_input("Dias (Baixo)", value=sla_configs['baixo_dias'], min_value=1)
            
            if st.form_submit_button("Atualizar Prazos de SLA"):
                supabase.table("sla_settings").upsert({"id": 1, "urgente_dias": dias_u, "normal_dias": dias_n, "baixo_dias": dias_b}).execute()
                st.success("Prazos atualizados! Os novos alertas já usarão esta regra.")
                st.rerun()

    with colB:
        st.subheader("📝 Solicitações de Acesso Pendentes")
        reqs_db = supabase.table("solicitacoes").select("*").execute().data
        pendentes = [r for r in reqs_db if r['status'] == 'pendente']
        if not pendentes:
            st.success("Nenhuma solicitação pendente no momento.")
        else:
            for req in pendentes:
                with st.expander(f"📌 {req['nome']}", expanded=True):
                    st.write(f"E-mail: {req['email']} | Data: {req['data']}")
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("✅ Aprovar", key=f"apr_{req['id']}"): aprovar_solicitacao_acesso(req['id'], req['email'], req['nome']); st.rerun()
                    with c2:
                        if st.button("❌ Rejeitar", key=f"rej_{req['id']}"): rejeitar_solicitacao_acesso(req['id']); st.rerun()

        st.markdown("---")
        st.subheader("📜 Histórico de Solicitações")
        historico = [r for r in reqs_db if r['status'] != 'pendente']
        if historico:
            df_hist = pd.DataFrame(historico)[['nome', 'email', 'status', 'data']]
            df_hist.columns = ['Nome', 'E-mail', 'Status', 'Data']
            def colorir_status_req(val): return f"color: {'green' if val == 'aprovado' else 'red'}; font-weight: bold;"
            try: st.dataframe(df_hist.style.map(colorir_status_req, subset=['Status']), use_container_width=True, hide_index=True)
            except: st.dataframe(df_hist.style.applymap(colorir_status_req, subset=['Status']), use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum histórico disponível.")

        st.markdown("---")
        st.subheader("📧 Diagnóstico de E-mail")
        if st.button("Enviar E-mail de Teste para Mim", use_container_width=True):
            remetente = st.secrets.get("EMAIL_SENDER", ""); senha = st.secrets.get("EMAIL_PASSWORD", "")
            if not remetente or not senha: st.error("❌ As chaves de e-mail estão vazias nos Secrets.")
            else:
                try:
                    server = smtplib.SMTP('smtp.gmail.com', 587); server.starttls(); server.login(remetente, senha)
                    msg = MIMEMultipart()
                    msg['From'] = remetente; msg['To'] = remetente; msg['Subject'] = "[TESTE] Conexão WEG"
                    msg.attach(MIMEText("A conexão com o Gmail está perfeita!", 'plain'))
                    server.send_message(msg); server.quit()
                    st.success(f"✅ E-mail de teste enviado com sucesso para: {remetente}")
                except Exception as e: st.error(f"❌ Erro do Google: {e}")

# ==========================================
# 7. ROTEADOR PRINCIPAL
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
