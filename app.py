import streamlit as st
import datetime
import pandas as pd
import plotly.express as px
from supabase import create_client, Client
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ==========================================
# 1. CONFIGURAÇÃO DA PÁGINA E CSS
# ==========================================
st.set_page_config(page_title="Central de Alertas - WEG", page_icon="🚨", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
        header[data-testid="stHeader"] { display: none !important; }
        .block-container { padding-top: 0rem !important; }
        section[data-testid="stMain"] .block-container > div[data-testid="stVerticalBlock"] > div:first-child {
            position: -webkit-sticky !important; position: sticky !important; top: 0px !important;
            background-color: #00579D !important; z-index: 99999 !important;
            padding: 1rem 2rem 1rem 2rem !important; margin-left: -3rem !important; margin-right: -3rem !important; margin-bottom: 2rem !important;
            border-bottom: 3px solid #003B6E !important; box-shadow: 0px 4px 10px rgba(0,0,0,0.15) !important;
        }
        section[data-testid="stMain"] .block-container > div[data-testid="stVerticalBlock"] > div:first-child h3,
        section[data-testid="stMain"] .block-container > div[data-testid="stVerticalBlock"] > div:first-child span,
        section[data-testid="stMain"] .block-container > div[data-testid="stVerticalBlock"] > div:first-child p { color: white !important; }
        section[data-testid="stMain"] .block-container > div[data-testid="stVerticalBlock"] > div:first-child button p { color: #333333 !important; }
        div[data-testid="stPopoverBody"] p, div[data-testid="stPopoverBody"] span, div[data-testid="stPopoverBody"] strong { color: #333333 !important; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. CONEXÃO E VARIÁVEIS DE SESSÃO
# ==========================================
@st.cache_resource
def init_connection() -> Client: return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

try: supabase = init_connection()
except Exception as e: st.error("⚠️ Erro de conexão."); st.stop()

if 'authenticated' not in st.session_state: st.session_state['authenticated'] = False
if 'must_change_password' not in st.session_state: st.session_state['must_change_password'] = False
if 'current_user' not in st.session_state: st.session_state['current_user'] = None
if 'menu_index' not in st.session_state: st.session_state['menu_index'] = 0
if 'sub_menu_prob' not in st.session_state: st.session_state['sub_menu_prob'] = "📋 Listagem de Alertas"
if 'sub_menu_colab' not in st.session_state: st.session_state['sub_menu_colab'] = "📋 Lista de Colaboradores"
if 'alerta_focus' not in st.session_state: st.session_state['alerta_focus'] = None
if 'notif_count' not in st.session_state: st.session_state['notif_count'] = 0

def teletransportar_para_alerta(alerta_id):
    st.session_state['alerta_focus'] = alerta_id
    st.session_state['sub_menu_prob'] = "🔍 Sala de Controle (Detalhes e Fórum)"
    st.session_state['menu_index'] = 1  
    st.rerun()

# ==========================================
# 3. MOTOR DE E-MAIL E ALERTAS DIÁRIOS
# ==========================================
def enviar_email(destinatario, assunto, mensagem_html):
    try:
        remetente = st.secrets.get("EMAIL_SENDER", ""); senha = st.secrets.get("EMAIL_PASSWORD", "")
        if not remetente or not senha: return
        msg = MIMEMultipart()
        msg['From'] = remetente; msg['To'] = destinatario if isinstance(destinatario, str) else ", ".join(destinatario); msg['Subject'] = assunto
        html_completo = f'<div style="font-family: Arial; color: #333; max-width: 600px; margin: auto; border: 1px solid #ddd;"><div style="background-color: #00579D; padding: 20px; color: white;"><h2>Central de Alertas - WEG</h2></div><div style="padding: 20px;">{mensagem_html}</div></div>'
        msg.attach(MIMEText(html_completo, 'html'))
        server = smtplib.SMTP('smtp.gmail.com', 587); server.starttls(); server.login(remetente, senha); server.send_message(msg); server.quit()
    except: pass

def enviar_notificacao(user_login, titulo, corpo, link="", send_email=True):
    try:
        supabase.table("notifications").insert({"user_login": user_login, "titulo": titulo, "corpo": corpo, "link": link, "lida": False}).execute()
        if send_email:
            resp = supabase.table("usuarios").select("email").eq("login", user_login).execute()
            if len(resp.data) > 0:
                enviar_email(resp.data[0]['email'], f"[WEG Alertas] {titulo}", f"<p>Você tem uma nova notificação:</p><div style='padding:15px; border-left: 4px solid #00579D;'><strong>{titulo}</strong><br>{corpo}</div>")
    except: pass

def enviar_notificacao_em_massa(lista_logins, titulo, corpo, link=""):
    try:
        emails_destino = []
        for user_login in lista_logins:
            supabase.table("notifications").insert({"user_login": user_login, "titulo": titulo, "corpo": corpo, "link": link, "lida": False}).execute()
            resp = supabase.table("usuarios").select("email").eq("login", user_login).execute()
            if len(resp.data) > 0: emails_destino.append(resp.data[0]['email'])
        if emails_destino:
            html_msg = f"<p>Olá Equipe,</p><p>Nova atualização no sistema:</p><div style='padding:15px; border-left: 4px solid #00579D;'><strong>{titulo}</strong><br>{corpo}</div>"
            enviar_email(emails_destino, f"[WEG Alertas - Equipe] {titulo}", html_msg)
    except: pass

# ---> LÓGICA DO RESUMO DIÁRIO <---
def processar_resumos_diarios():
    users = supabase.table("usuarios").select("*").eq("ativo", True).execute().data
    probs = {p['id']: p['titulo'] for p in supabase.table("problemas").select("id, titulo").execute().data}
    enviados = 0
    
    for u in users:
        login, email, nome = u['login'], u['email'], u['nome']
        
        # Busca Ações Principais
        resp_db = supabase.table("problem_action_responsibles").select("action_id").eq("colaborador_login", login).execute().data
        action_ids = [r['action_id'] for r in resp_db] if resp_db else []
        acoes_pend = []
        if action_ids:
            acoes_db = supabase.table("problem_actions").select("*").in_("id", action_ids).execute().data
            acoes_pend = [a for a in acoes_db if a['status'] not in ['solucionada', 'solucionado']]
            
        # Busca Tarefas
        tarefas_pend = supabase.table("action_tasks").select("*").eq("responsavel_login", login).eq("status", "pendente").execute().data
        
        if not acoes_pend and not tarefas_pend: continue # Se a pessoa não deve nada, não recebe email
            
        html = f"<p>Olá <b>{nome}</b>,</p><p>Este é o seu resumo atualizado de pendências na Central de Alertas.</p>"
        
        if acoes_pend:
            html += "<h3>🛠️ Suas Ações Principais</h3><ul>"
            for a in acoes_pend:
                st_cor = "orange" if a['status'] == 'liberada' else "red"
                html += f"<li><strong>{a['descricao']}</strong><br><span style='font-size:12px; color:gray;'>Origem: Alerta #{a['problem_id']} ({probs.get(a['problem_id'], '')}) | Prazo: <b>{a['prazo'][:10]}</b> | Status: <span style='color:{st_cor};'>{a['status'].upper()}</span></span></li><br>"
            html += "</ul>"
            
        if tarefas_pend:
            html += "<h3>📌 Suas Tarefas (Sub-ações)</h3><ul>"
            for t in tarefas_pend:
                html += f"<li><strong>{t['descricao']}</strong><br><span style='font-size:12px; color:gray;'>Origem: Ação Corretiva #{t['action_id']}</span></li><br>"
            html += "</ul>"
            
        html += "<p>Acesse o painel do sistema para registrar as execuções. Bom trabalho!</p>"
        enviar_email(email, "⏰ Suas Pendências Diárias - WEG Alertas", html)
        enviados += 1
        
    return enviados

def checar_disparo_automatico():
    try:
        config = supabase.table("system_config").select("*").eq("id", 1).execute().data
        hoje = datetime.datetime.now().strftime("%Y-%m-%d")
        if config and config[0].get("last_daily_email") != hoje:
            supabase.table("system_config").update({"last_daily_email": hoje}).eq("id", 1).execute()
            processar_resumos_diarios()
    except: pass

# Chama a checagem invisível toda vez que a página roda
checar_disparo_automatico()

# ==========================================
# 4. FUNÇÕES DE AUTENTICAÇÃO
# ==========================================
def fazer_login(usuario_login, senha):
    usuario_login = usuario_login.strip().lower() 
    resposta = supabase.table("usuarios").select("*").eq("login", usuario_login).execute()
    if len(resposta.data) > 0:
        usuario = resposta.data[0]
        if usuario.get('ativo', True) and usuario.get('senha') == senha:
            st.session_state['authenticated'] = True
            st.session_state['current_user'] = {"login": usuario['login'], "nome": usuario['nome'], "area": usuario['area'], "role": usuario['role']}
            st.session_state['must_change_password'] = (senha == "WEG2026")
            return True
    return False

def fazer_logout():
    st.session_state['authenticated'] = False; st.session_state['must_change_password'] = False
    st.session_state['current_user'] = None; st.session_state['menu_index'] = 0; st.rerun()

def aprovar_solicitacao_acesso(req_id, req_email, req_nome):
    supabase.table("solicitacoes").update({"status": "aprovado"}).eq("id", req_id).execute()
    login_extraido = req_email.strip().lower().split('@')[0]
    check = supabase.table("usuarios").select("login").eq("login", login_extraido).execute()
    if len(check.data) == 0:
        supabase.table("usuarios").insert({"login": login_extraido, "nome": req_nome, "email": req_email, "senha": "WEG2026", "area": "A definir", "role": "User", "ativo": True}).execute()
        enviar_email(req_email, "Acesso Aprovado", f"Olá {req_nome},<br><br>Seu acesso foi aprovado. Usuário: <b>{login_extraido}</b> | Senha: <b>WEG2026</b>")

def rejeitar_solicitacao_acesso(req_id):
    supabase.table("solicitacoes").update({"status": "rejeitado"}).eq("id", req_id).execute()

# ==========================================
# 5. TELAS DE LOGIN
# ==========================================
def render_login():
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.write("<br><br>", unsafe_allow_html=True)
        try: st.image("logo_weg.png", width=200)
        except: st.markdown("### [LOGO WEG]")
        st.markdown("<h2 style='color: #00579D;'>Central de Alertas</h2>", unsafe_allow_html=True)
        
        aba_login, aba_solicitar = st.tabs(["🔐 Entrar", "📝 Solicitar Acesso"])
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
                        st.success("Solicitação enviada! Aguarde a aprovação.")
                    else: st.warning("Preencha todos os campos obrigatórios.")

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
                    st.success("Senha alterada com sucesso!"); st.rerun()

# ==========================================
# 6. COMPONENTES DE LAYOUT E ROTEADOR
# ==========================================
def render_header():
    header_container = st.container()
    with header_container:
        col1, col2, col3 = st.columns([7, 2, 2])
        with col1: st.markdown("<h3 style='margin-bottom: 0px;'>Central de Alertas WEG</h3>", unsafe_allow_html=True)
        with col2: 
            try:
                notifs = supabase.table("notifications").select("*").eq("user_login", st.session_state['current_user']['login']).eq("lida", False).order("id", desc=True).execute().data
                qtd = len(notifs)
            except: notifs = []; qtd = 0
            if qtd > st.session_state['notif_count']: st.toast("Você tem novas notificações!", icon="🔔")
            st.session_state['notif_count'] = qtd
            cor_sino = "🔴" if qtd > 0 else "⚪"
            with st.popover(f"🔔 {qtd} Novas" if qtd > 0 else "🔔 Nenhuma", use_container_width=True):
                st.markdown(f"**Suas Notificações {cor_sino}**")
                if qtd == 0: st.info("Tudo limpo por aqui!")
                else:
                    for n in notifs:
                        st.warning(f"**{n['titulo']}**\n\n{n['corpo']}")
                        if st.button("Acessar Link" if n['link'] else "Marcar como Lida", key=f"read_{n['id']}", type="primary"):
                            supabase.table("notifications").update({"lida": True}).eq("id", n['id']).execute()
                            if n['link'].startswith("Problemas") or n['link'].startswith("Fórum"):
                                st.session_state['alerta_focus'] = int(n['link'].split("|")[1]) if len(n['link'].split("|")) > 1 else None
                                st.session_state['sub_menu_prob'] = "🔍 Sala de Controle (Detalhes e Fórum)"
                                st.session_state['menu_index'] = 1
                            elif n['link'] == "Minhas Ações": st.session_state['menu_index'] = 2
                            st.rerun()
        with col3: 
            st.markdown(f"<div style='text-align: right; line-height: 1.2;'><strong style='font-size: 16px;'>👤 {st.session_state['current_user']['nome']}</strong><br><span style='font-size:12px; opacity: 0.8;'>{st.session_state['current_user']['area']}</span></div>", unsafe_allow_html=True)
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
# 7. PÁGINAS DO SISTEMA
# ==========================================
def pagina_dashboard():
    st.header("📊 Painel de Gestão (Dashboard)")
    user_role, user_area = st.session_state['current_user']['role'], st.session_state['current_user']['area']
    probs_data = supabase.table("problemas").select("*").execute().data if user_role == 'Admin' else supabase.table("problemas").select("*").eq("area", user_area).execute().data
    
    st.markdown(f"*Visão {'Global (Admin)' if user_role == 'Admin' else f'Filtrada: {user_area}'}*")
    if not probs_data: st.info("Nenhum alerta registrado para compor o Dashboard no momento."); return

    df = pd.DataFrame(probs_data)
    df['criado_em'], df['sla_due_at'] = pd.to_datetime(df['criado_em']), pd.to_datetime(df['sla_due_at'])
    hoje = datetime.datetime.now()

    abertos = len(df[df['status'] == 'aberto'])
    em_andamento = len(df[df['status'] == 'aprovado'])
    solucionados = len(df[df['status'] == 'solucionado'])
    vencidos = len(df[(df['sla_due_at'] < hoje) & (~df['status'].isin(['solucionado', 'rejeitado']))])

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.info(f"### 🚨 {abertos}\n**Aguardando Triagem**")
    with c2: st.warning(f"### ⚙️ {em_andamento}\n**Em Andamento**")
    with c3: st.error(f"### 🔥 {vencidos}\n**Vencidos no SLA**")
    with c4: st.success(f"### ✅ {solucionados}\n**Solucionados**")

    st.markdown("---")
    st.markdown("### 📈 Análise Gráfica")
    g1, g2, g3 = st.columns(3)
    with g1:
        st.markdown("**1. Distribuição por Status**")
        df_status = df['status'].str.upper().value_counts().reset_index(); df_status.columns = ['Status', 'Quantidade']
        st.bar_chart(df_status.set_index('Status'), color="#00579D")
    with g2:
        st.markdown("**2. Nível de Prioridade**")
        df_prio = df['prioridade'].value_counts().reset_index(); df_prio.columns = ['Prioridade', 'Quantidade']
        st.bar_chart(df_prio.set_index('Prioridade'), color="#00a0e3")
    with g3:
        st.markdown("**3. Demanda por Área**")
        df_area = df['area'].value_counts().reset_index(); df_area.columns = ['Área', 'Quantidade']
        st.bar_chart(df_area.set_index('Área'), color="#003B6E")

    st.markdown("---")
    st.subheader("🔥 Fila de Alertas Críticos")
    df_criticos = df[~df['status'].isin(['solucionado', 'rejeitado'])].copy()
    if not df_criticos.empty:
        df_criticos['peso'] = df_criticos['prioridade'].map({"Urgente": 1, "Normal": 2, "Baixo": 3})
        for _, row in df_criticos.sort_values(by=['peso', 'sla_due_at']).head(10).iterrows():
            with st.container(border=True):
                col_info, col_dados, col_btn = st.columns([5, 2, 2])
                with col_info:
                    st.markdown(f"#### 🚨 #{row['id']} - {row['titulo']}")
                    st.caption(f"📍 Área: **{row['area']}** | Aberto em: {row['criado_em'].strftime('%d/%m/%Y')}")
                with col_dados:
                    cor_prio = "red" if row['prioridade'] == "Urgente" else "orange" if row['prioridade'] == "Normal" else "green"
                    st.markdown(f"<h4 style='color: {cor_prio}; margin-bottom: 0px;'>{row['prioridade'].upper()}</h4>", unsafe_allow_html=True)
                    st.caption(f"Vence em: {row['sla_due_at'].strftime('%d/%m/%Y')}")
                with col_btn:
                    st.write("<br>", unsafe_allow_html=True)
                    if st.button("Tratar Alerta ➔", key=f"d_prob_{row['id']}", use_container_width=True, type="primary"): teletransportar_para_alerta(row['id'])
    else: st.success("🎉 Tudo sob controle! Nenhum alerta crítico pendente.")

def pagina_problemas():
    st.header("⚠️ Gestão de Problemas e Alertas")
    try: areas = [l['nome'] for l in supabase.table("locais").select("nome").order("nome").execute().data]
    except: areas = ["Geral"]
    try: sla_configs = supabase.table("sla_settings").select("*").eq("id", 1).execute().data[0]
    except: sla_configs = {"urgente_dias": 1, "normal_dias": 3, "baixo_dias": 5}

    opcoes_sub = ["📋 Listagem de Alertas", "➕ Abrir Novo Alerta", "🔍 Sala de Controle (Detalhes e Fórum)"]
    if st.session_state['sub_menu_prob'] not in opcoes_sub: st.session_state['sub_menu_prob'] = opcoes_sub[0]

    cols_btn = st.columns(len(opcoes_sub))
    for i, opcao in enumerate(opcoes_sub):
        if cols_btn[i].button(opcao, type="primary" if st.session_state['sub_menu_prob'] == opcao else "secondary", use_container_width=True, key=f"btn_s_prob_{i}"):
            st.session_state['sub_menu_prob'] = opcao; st.rerun()

    aba_atual = st.session_state['sub_menu_prob']
    st.markdown("---")
    
    if aba_atual == "📋 Listagem de Alertas":
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
                    st.dataframe(df_display, use_container_width=True, hide_index=True, height=400)
                    st.markdown("### 🚀 Acesso Rápido")
                    col1, col2 = st.columns([1, 4])
                    with col1:
                        id_rapido = st.selectbox("ID do Alerta:", [str(p['id']) for p in problemas_db])
                        if st.button("Abrir Sala de Controle", type="primary", use_container_width=True): teletransportar_para_alerta(int(id_rapido))
                else: st.info("Nenhum alerta com estes filtros.")
            else: st.info("Nenhum problema cadastrado.")
        except Exception as e: st.error(f"Erro: {str(e)}")

    elif aba_atual == "➕ Abrir Novo Alerta":
        with st.form("form_novo_prob"):
            titulo = st.text_input("Título do Alerta / Problema*")
            descricao = st.text_area("Descrição detalhada*")
            col1, col2 = st.columns(2)
            with col1: area_prob = st.selectbox("Área/Local afetado*", areas)
            with col2: prioridade = st.selectbox("Prioridade*", ["Urgente", "Normal", "Baixo"])
            anexo = st.file_uploader("Anexar Evidência (Imagem, PDF, Excel)", type=['png','jpg','pdf','xlsx'])
            
            if st.form_submit_button("Abrir Alerta", type="primary"):
                if titulo and descricao:
                    dias_adicionais = sla_configs['urgente_dias'] if prioridade == "Urgente" else sla_configs['normal_dias'] if prioridade == "Normal" else sla_configs['baixo_dias']
                    prazo = datetime.datetime.now() + datetime.timedelta(days=dias_adicionais)
                    try:
                        res = supabase.table("problemas").insert({
                            "titulo": titulo, "descricao": descricao, "area": area_prob,
                            "prioridade": prioridade, "status": "aberto", "criado_por": st.session_state['current_user']['login'],
                            "criado_em": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "sla_due_at": prazo.strftime("%Y-%m-%d %H:%M:%S"), "anexo": anexo.name if anexo else None
                        }).execute()
                        st.success("✅ Alerta registrado com sucesso!")
                        teletransportar_para_alerta(res.data[0]['id'])
                    except Exception as e: st.error(f"Erro no BD: {str(e)}")
                else: st.warning("Título e Descrição são obrigatórios.")

    elif aba_atual == "🔍 Sala de Controle (Detalhes e Fórum)":
        try:
            problemas_db = supabase.table("problemas").select("*").order("id", desc=True).execute().data
            users_all = supabase.table("usuarios").select("login, nome, ativo").execute().data
            
            if problemas_db:
                opcoes_ids = [""] + [str(p['id']) + f" - {p['titulo']}" for p in problemas_db]
                idx_padrao = 0
                if st.session_state['alerta_focus']:
                    for i, opt in enumerate(opcoes_ids):
                        if opt.startswith(str(st.session_state['alerta_focus']) + " -"): idx_padrao = i; break

                id_selecionado = st.selectbox("Selecione o Alerta para operar a Sala de Controle:", opcoes_ids, index=idx_padrao, on_change=lambda: st.session_state.update({'alerta_focus': None}))
                
                if id_selecionado != "":
                    alerta = next((p for p in problemas_db if p['id'] == int(id_selecionado.split(" - ")[0])), None)
                    if alerta:
                        st.markdown(f"### #{alerta['id']} - {alerta['titulo']}")
                        st.markdown("---")
                        col_esq, col_dir = st.columns([6, 4], gap="large")
                        
                        with col_esq:
                            c1, c2, c3, c4 = st.columns(4)
                            c1.metric("Área", alerta['area']); c2.metric("Prioridade", alerta['prioridade'])
                            c3.metric("Status", alerta['status'].upper()); c4.metric("SLA", alerta['sla_due_at'][:10])
                            st.info(alerta['descricao'])
                            if alerta['anexo']: st.markdown(f"📎 **Anexo:** `{alerta['anexo']}`")
                            st.write("<br>", unsafe_allow_html=True)
                            
                            if alerta['status'] == 'aberto':
                                st.markdown("#### ⚙️ Análise do Facilitador")
                                is_admin = st.session_state['current_user']['role'] == 'Admin'
                                fac_resp = supabase.table("area_facilitadores").select("facilitador_login").eq("area", alerta['area']).execute()
                                is_facilitator = st.session_state['current_user']['login'] == (fac_resp.data[0]['facilitador_login'] if fac_resp.data else None)
                                
                                if st.session_state['current_user']['login'] == alerta['criado_por'] and not is_admin: st.warning("⚠️ Você não pode aprovar seu próprio alerta.")
                                elif not is_admin and not is_facilitator: st.warning("⚠️ Apenas Admin ou Facilitador da área aprovam.")
                                else:
                                    c_apr, c_rej = st.columns(2)
                                    with c_apr:
                                        if st.button("✅ Aprovar Alerta", use_container_width=True, type="primary"):
                                            supabase.table("problemas").update({"status": "aprovado"}).eq("id", alerta['id']).execute()
                                            enviar_notificacao(alerta['criado_por'], "Alerta Aprovado", f"O alerta #{alerta['id']} foi aprovado.", f"Problemas|{alerta['id']}")
                                            st.rerun()
                                    with c_rej:
                                        with st.popover("❌ Rejeitar", use_container_width=True):
                                            motivo = st.text_area("Motivo da Rejeição*")
                                            if st.button("Confirmar Rejeição") and motivo:
                                                supabase.table("problemas").update({"status": "rejeitado"}).eq("id", alerta['id']).execute()
                                                supabase.table("problem_justifications").insert({"problem_id": alerta['id'], "autor": st.session_state['current_user']['login'], "acao": "rejeitado", "motivo": motivo}).execute()
                                                enviar_notificacao(alerta['criado_por'], "Alerta Rejeitado", f"O alerta #{alerta['id']} foi rejeitado. Motivo: {motivo}", f"Problemas|{alerta['id']}")
                                                st.rerun()
                            
                            elif alerta['status'] == 'rejeitado':
                                just_db = supabase.table("problem_justifications").select("*").eq("problem_id", alerta['id']).eq("acao", "rejeitado").execute().data
                                st.error(f"🚨 **ALERTA REJEITADO (Fechado)**\n\n**Motivo:** {just_db[-1]['motivo'] if just_db else 'Sem motivo registrado.'}")
                                
                            elif alerta['status'] in ['aprovado', 'solucionado']:
                                st.markdown("#### ✅ Plano de Ações Corretivas")
                                acoes_db = supabase.table("problem_actions").select("*").eq("problem_id", alerta['id']).execute().data
                                
                                if acoes_db:
                                    for acao in acoes_db:
                                        cor_st = "🔴" if acao['status']=='bloqueada' else "🟢" if acao['status']=='solucionada' else "🟠"
                                        texto_st = "BLOQUEADA" if acao['status']=='bloqueada' else "LIBERADA" if acao['status'] in ['liberada', 'pendente'] else "SOLUCIONADA"
                                        
                                        with st.expander(f"{cor_st} Ação #{acao['id']}: {acao['descricao']} | Status: {texto_st}", expanded=True):
                                            logins_resp = [r['colaborador_login'] for r in supabase.table("problem_action_responsibles").select("colaborador_login").eq("action_id", acao['id']).execute().data]
                                            st.write(f"**Responsáveis:** {', '.join([u['nome'] for u in users_all if u['login'] in logins_resp])}")
                                            if acao.get('depende_de_id'): st.write(f"🔗 *Depende da conclusão da Ação #{acao['depende_de_id']}*")
                                            
                                            is_admin = st.session_state['current_user']['role'] == 'Admin'
                                            is_action_resp = st.session_state['current_user']['login'] in logins_resp
                                            
                                            st.markdown("##### 📌 Tarefas Delegadas")
                                            try: tarefas_db = supabase.table("action_tasks").select("*").eq("action_id", acao['id']).order("id").execute().data
                                            except: tarefas_db = []
                                            if tarefas_db:
                                                for t in tarefas_db:
                                                    resp_nome = next((u['nome'] for u in users_all if u['login'] == t['responsavel_login']), t['responsavel_login'])
                                                    icone_t = "✅" if t['status'] == 'executada' else "❌" if t['status'] == 'nao_executada' else "⏳"
                                                    st.write(f"{icone_t} **{t['descricao']}** (Resp: {resp_nome})")
                                                    if t['status'] != 'pendente':
                                                        st.caption(f"**Resp:** {t.get('resolucao_texto', '')}")
                                                        if t.get('precisa_nova_acao'): st.warning("⚠️ Solicitada nova Ação Principal.")
                                            else: st.caption("Nenhuma tarefa delegada.")

                                            if is_admin or is_action_resp:
                                                if acao['status'] != 'bloqueada':
                                                    with st.popover("➕ Delegar Tarefa", use_container_width=True):
                                                        t_desc = st.text_input("O que deve ser feito?", key=f"tdesc_{acao['id']}")
                                                        t_resp = st.selectbox("Responsável", [u['login'] for u in users_all if u['ativo']], format_func=lambda x: next(u['nome'] for u in users_all if u['login']==x), key=f"tresp_{acao['id']}")
                                                        if st.button("Salvar Tarefa", key=f"tbtn_{acao['id']}", type="primary"):
                                                            supabase.table("action_tasks").insert({"action_id": acao['id'], "descricao": t_desc, "responsavel_login": t_resp}).execute()
                                                            enviar_notificacao(t_resp, "Nova Tarefa 📌", f"Você tem uma tarefa: '{t_desc}'", "Minhas Ações")
                                                            st.rerun()
                                                st.markdown("---")
                                                if acao['status'] == 'bloqueada': st.error("🔒 Ação bloqueada.")
                                                else:
                                                    with st.form(f"f_acao_{acao['id']}"):
                                                        opcs = ["pendente", "liberada", "em_andamento", "solucionado", "solucionada"]
                                                        idx_st = opcs.index(acao['status']) if acao['status'] in opcs else 1
                                                        novo_status = st.selectbox("Status", ["liberada", "solucionada"], index=0 if idx_st < 3 else 1)
                                                        nova_obs = st.text_area("Observações", value=acao['observacao'] if acao['observacao'] else "")
                                                        if st.form_submit_button("Atualizar Ação"):
                                                            supabase.table("problem_actions").update({"status": novo_status, "observacao": nova_obs}).eq("id", acao['id']).execute()
                                                            if novo_status == 'solucionada' and acao['status'] not in ['solucionada', 'solucionado']:
                                                                deps = supabase.table("problem_actions").select("id, descricao").eq("depende_de_id", acao['id']).execute().data
                                                                if deps:
                                                                    for d in deps:
                                                                        supabase.table("problem_actions").update({"status": "liberada"}).eq("id", d['id']).execute()
                                                                        resps_d = supabase.table("problem_action_responsibles").select("colaborador_login").eq("action_id", d['id']).execute().data
                                                                        enviar_notificacao_em_massa([r['colaborador_login'] for r in resps_d], "Ação Liberada! 🟢", f"Agora é com você: '{d['descricao']}'", "Minhas Ações")
                                                                enviar_notificacao(alerta['criado_por'], "Ação Concluída ✅", f"Ação finalizada!", f"Problemas|{alerta['id']}")
                                                            st.rerun()
                                            else: st.info("Apenas responsáveis editam."); st.write(f"Obs: {acao['observacao']}")

                                st.markdown("##### ➕ Adicionar Nova Ação Principal")
                                with st.form("form_nova_acao"):
                                    desc_acao = st.text_input("O que deve ser feito?")
                                    colP, colD = st.columns(2)
                                    with colP: prazo_acao = st.date_input("Prazo final")
                                    with colD: 
                                        opcoes_dep = {"": "Nenhuma"}
                                        if acoes_db: opcoes_dep.update({str(a['id']): f"#{a['id']} - {a['descricao'][:30]}" for a in acoes_db})
                                        dep_selecionada = st.selectbox("Depende de qual ação?", list(opcoes_dep.keys()), format_func=lambda x: opcoes_dep[x])
                                        
                                    selecionados = st.multiselect("Responsáveis", [u['login'] for u in users_all if u['ativo']], format_func=lambda x: next(u['nome'] for u in users_all if u['login']==x))
                                    if st.form_submit_button("Salvar Ação"):
                                        if desc_acao and selecionados:
                                            status_ini = "bloqueada" if dep_selecionada != "" else "liberada"
                                            res = supabase.table("problem_actions").insert({"problem_id": alerta['id'], "descricao": desc_acao, "status": status_ini, "prazo": str(prazo_acao), "criado_por": st.session_state['current_user']['login'], "depende_de_id": int(dep_selecionada) if dep_selecionada else None}).execute()
                                            for resp_log in selecionados:
                                                supabase.table("problem_action_responsibles").insert({"action_id": res.data[0]['id'], "colaborador_login": resp_log}).execute()
                                            if status_ini == "liberada": enviar_notificacao_em_massa(selecionados, "Nova Ação 📋", f"Resolver: '{desc_acao}'", "Minhas Ações")
                                            st.success("Salva!"); st.rerun()
                                        else: st.error("Preencha descrição e responsáveis.")

                        with col_dir:
                            st.markdown("#### 💬 Fórum de Insights")
                            reply_key = f"reply_focus_{alerta['id']}"
                            if reply_key not in st.session_state: st.session_state[reply_key] = None

                            with st.container(height=500):
                                comments_db = supabase.table("problem_comments").select("*").eq("problem_id", alerta['id']).order("id", desc=False).execute().data
                                if comments_db:
                                    for c in comments_db:
                                        usr_nome = next((u['nome'] for u in users_all if u['login'] == c['autor']), c['autor'])
                                        is_me = c['autor'] == st.session_state['current_user']['login']
                                        with st.chat_message("user" if is_me else "assistant", avatar="🧑‍💻" if is_me else "💡"):
                                            st.markdown(f"**{'Você' if is_me else usr_nome}** *({c['criado_em'][:16].replace('T', ' ')})*")
                                            st.write(c['texto'])
                                            if st.button("↩️ Responder", key=f"btn_rep_{c['id']}"):
                                                st.session_state[reply_key] = {"nome": 'Você' if is_me else usr_nome, "texto": c['texto']}; st.rerun()
                                else: st.info("Nenhum insight ainda.")
                            
                            st.write("<br>", unsafe_allow_html=True)
                            if st.session_state[reply_key]:
                                st.info(f"↩️ **Respondendo:** _{st.session_state[reply_key]['texto'][:50]}..._")
                                if st.button("❌ Cancelar"): st.session_state[reply_key] = None; st.rerun()

                            with st.form(key=f"form_chat_{alerta['id']}", clear_on_submit=True):
                                txt_msg = st.text_input("Escreva seu insight...")
                                notificar_email = st.checkbox("🔔 Avisar autor por e-mail", value=False)
                                if st.form_submit_button("Enviar Mensagem") and txt_msg:
                                    final_msg = f"> **Resp:** _{st.session_state[reply_key]['texto']}_\n\n{txt_msg}" if st.session_state[reply_key] else txt_msg
                                    supabase.table("problem_comments").insert({"problem_id": alerta['id'], "autor": st.session_state['current_user']['login'], "texto": final_msg}).execute()
                                    st.session_state[reply_key] = None 
                                    if st.session_state['current_user']['login'] != alerta['criado_por']:
                                        enviar_notificacao(alerta['criado_por'], "Novo Insight 💡", "Alguém comentou no seu Alerta.", f"Problemas|{alerta['id']}", send_email=notificar_email)
                                    st.rerun()
        except Exception as e: st.error(f"Erro na Sala de Controle: {e}")

def pagina_acoes():
    st.header("🎯 Meu Painel de Execução")
    st.markdown("Gerencie suas responsabilidades. Navegue pelas abas para separar Ações Principais, Tarefas e Histórico.")
    meu_login = st.session_state['current_user']['login']
    
    try:
        tarefas_db = supabase.table("action_tasks").select("*").eq("responsavel_login", meu_login).execute().data
        df_tarefas = pd.DataFrame(tarefas_db) if tarefas_db else pd.DataFrame()
        resp_db = supabase.table("problem_action_responsibles").select("action_id").eq("colaborador_login", meu_login).execute().data
        action_ids = [r['action_id'] for r in resp_db] if resp_db else []
        acoes_db = supabase.table("problem_actions").select("*").in_("id", action_ids).execute().data if action_ids else []
        df_acoes = pd.DataFrame(acoes_db) if acoes_db else pd.DataFrame()
        probs_db = supabase.table("problemas").select("id, titulo").execute().data
        prob_map = {p['id']: p['titulo'] for p in probs_db} if probs_db else {}
    except Exception as e: st.error(f"Erro ao carregar dados: {e}"); return

    df_acoes_ativas, df_acoes_concluidas = pd.DataFrame(), pd.DataFrame()
    if not df_acoes.empty:
        df_acoes_ativas = df_acoes[df_acoes['status'].isin(['pendente', 'liberada', 'bloqueada', 'em_andamento'])]
        df_acoes_concluidas = df_acoes[df_acoes['status'].isin(['solucionada', 'solucionado'])]

    df_tarefas_ativas, df_tarefas_concluidas = pd.DataFrame(), pd.DataFrame()
    if not df_tarefas.empty:
        df_tarefas_ativas = df_tarefas[df_tarefas['status'] == 'pendente']
        df_tarefas_concluidas = df_tarefas[df_tarefas['status'].isin(['executada', 'nao_executada'])]

    tab_a, tab_t, tab_h = st.tabs(["🛠️ Ações Principais", "📌 Tarefas (Sub-ações)", "✅ Histórico (Concluídas)"])

    with tab_a:
        if not df_acoes_ativas.empty:
            col_graf, col_lista = st.columns([1, 2], gap="large")
            with col_graf:
                st.markdown("**Performance: Status das Ações**")
                df_pie = df_acoes_ativas['status'].str.upper().value_counts().reset_index()
                df_pie.columns = ['Status', 'Quantidade']
                fig_a = px.pie(df_pie, names='Status', values='Quantidade', hole=0.4, color_discrete_sequence=["#00579D", "#FFC107", "#DC3545"])
                fig_a.update_layout(margin=dict(t=0, b=0, l=0, r=0))
                st.plotly_chart(fig_a, use_container_width=True)
            with col_lista:
                for _, acao in df_acoes_ativas.iterrows():
                    titulo_prob = prob_map.get(acao['problem_id'], "Alerta Excluído")
                    cor_status = "🔴" if acao['status'] == 'bloqueada' else "🟠"
                    with st.container(border=True):
                        st.markdown(f"#### {cor_status} Ação #{acao['id']} - {acao['descricao']}")
                        c1, c2 = st.columns([3, 1])
                        c1.caption(f"**Origem:** Alerta #{acao['problem_id']} ({titulo_prob})")
                        c1.caption(f"**Prazo:** {acao['prazo'][:10]}")
                        c2.write(f"Status: **{acao['status'].upper()}**")
                        if st.button("Abrir Alerta e Tratar Ação ➔", key=f"jump_a_{acao['id']}", type="primary"): teletransportar_para_alerta(acao['problem_id'])
        else: st.success("🎉 Você não tem Ações Principais em andamento!")

    with tab_t:
        if not df_tarefas_ativas.empty:
            col_graf_t, col_lista_t = st.columns([1, 2], gap="large")
            with col_graf_t:
                st.markdown("**Volume de Tarefas por Ação Origem**")
                df_pie_t = df_tarefas_ativas['action_id'].value_counts().reset_index()
                df_pie_t.columns = ['Ação ID', 'Quantidade']
                df_pie_t['Ação ID'] = 'Ação #' + df_pie_t['Ação ID'].astype(str)
                fig_t = px.pie(df_pie_t, names='Ação ID', values='Quantidade', hole=0.4, color_discrete_sequence=px.colors.sequential.Teal)
                fig_t.update_layout(margin=dict(t=0, b=0, l=0, r=0))
                st.plotly_chart(fig_t, use_container_width=True)
            with col_lista_t:
                for _, t in df_tarefas_ativas.iterrows():
                    with st.container(border=True):
                        st.markdown(f"#### ⏳ Tarefa: {t['descricao']}")
                        st.caption(f"Pertence à Ação Corretiva #{t['action_id']}")
                        with st.popover("📝 Registrar Execução", use_container_width=True):
                            t_status = st.radio("Status de Conclusão", ["Executada", "Não executada"], key=f"rad_{t['id']}")
                            t_obs = st.text_area("Explique o que foi realizado*", key=f"obs_{t['id']}")
                            t_nova_acao = st.checkbox("Necessita de uma nova Ação Principal?", key=f"chk_{t['id']}") if t_status == "Não executada" else False
                            if st.button("Salvar Resolução", key=f"btn_salvar_{t['id']}", type="primary"):
                                if not t_obs: st.error("O texto explicativo é obrigatório.")
                                else:
                                    db_status = 'executada' if t_status == 'Executada' else 'nao_executada'
                                    supabase.table("action_tasks").update({"status": db_status, "resolucao_texto": t_obs, "precisa_nova_acao": t_nova_acao}).eq("id", t['id']).execute()
                                    try:
                                        acao_pai = supabase.table("problem_actions").select("descricao, criado_por").eq("id", t['action_id']).execute().data[0]
                                        enviar_notificacao(acao_pai['criado_por'], "Tarefa Respondida 📌", f"A tarefa '{t['descricao']}' foi marcada como {t_status}.")
                                    except: pass
                                    st.rerun()
        else: st.success("🎉 Nenhuma tarefa delegada pendente!")

    with tab_h:
        colA, colB = st.columns(2, gap="large")
        with colA:
            st.subheader("✅ Ações Finalizadas")
            if not df_acoes_concluidas.empty:
                for _, acao in df_acoes_concluidas.iterrows():
                    titulo_prob = prob_map.get(acao['problem_id'], "Excluído")
                    with st.container(border=True):
                        st.markdown(f"**Ação #{acao['id']} - {acao['descricao']}**")
                        st.caption(f"Origem: Alerta #{acao['problem_id']} ({titulo_prob})")
                        st.info(f"**Observação Final:** {acao['observacao'] if acao['observacao'] else 'Nenhuma.'}")
            else: st.write("Nenhuma ação finalizada.")
        with colB:
            st.subheader("📌 Tarefas Respondidas")
            if not df_tarefas_concluidas.empty:
                for _, t in df_tarefas_concluidas.iterrows():
                    cor = "green" if t['status'] == 'executada' else "red"
                    with st.container(border=True):
                        st.markdown(f"**Tarefa:** {t['descricao']}")
                        st.markdown(f"Status: <strong style='color:{cor};'>{t['status'].upper().replace('_',' ')}</strong>", unsafe_allow_html=True)
                        st.caption(f"**Sua resposta:** {t.get('resolucao_texto', '')}")
            else: st.write("Nenhuma tarefa respondida.")

def pagina_colaboradores():
    st.header("👥 Gestão de Colaboradores")
    is_admin = st.session_state['current_user']['role'] == 'Admin'
    opcoes_sub = ["📋 Lista de Colaboradores", "➕ Adicionar Novo", "✏️ Editar / Desativar"] if is_admin else ["📋 Lista de Colaboradores"]
    if st.session_state['sub_menu_colab'] not in opcoes_sub: st.session_state['sub_menu_colab'] = opcoes_sub[0]

    cols_btn = st.columns(len(opcoes_sub))
    for i, opcao in enumerate(opcoes_sub):
        if cols_btn[i].button(opcao, type="primary" if st.session_state['sub_menu_colab'] == opcao else "secondary", use_container_width=True, key=f"b_colab_{i}"):
            st.session_state['sub_menu_colab'] = opcao; st.rerun()

    aba_atual = st.session_state['sub_menu_colab']
    st.markdown("---")
    
    users_db = supabase.table("usuarios").select("*").execute().data
    try: areas = [l['nome'] for l in supabase.table("locais").select("nome").order("nome").execute().data]
    except: areas = ["A definir"]
    
    if aba_atual == "📋 Lista de Colaboradores":
        if users_db:
            df_users = pd.DataFrame(users_db)[['login', 'nome', 'email', 'area', 'role', 'ativo']]
            df_users.columns = ['Usuário', 'Nome Completo', 'E-mail', 'Área / Setor', 'Papel', 'Status Ativo']
            try: st.dataframe(df_users.style.map(lambda v: f"color: {'green' if v else 'red'}", subset=['Status Ativo']), use_container_width=True, hide_index=True, height=400)
            except: st.dataframe(df_users.style.applymap(lambda v: f"color: {'green' if v else 'red'}", subset=['Status Ativo']), use_container_width=True, hide_index=True, height=400)

    if is_admin:
        if aba_atual == "➕ Adicionar Novo":
            with st.form("form_add_colab"):
                col1, col2 = st.columns(2)
                with col1: novo_nome = st.text_input("Nome Completo*"); novo_email = st.text_input("E-mail corporativo*")
                with col2: novo_area = st.selectbox("Área / Setor*", areas); novo_papel = st.selectbox("Papel*", ["User", "Facilitador", "Admin"])
                if st.form_submit_button("Salvar Colaborador"):
                    if novo_nome and novo_email:
                        novo_login = novo_email.strip().lower().split('@')[0]
                        if len(supabase.table("usuarios").select("login").eq("login", novo_login).execute().data) == 0:
                            supabase.table("usuarios").insert({"login": novo_login, "nome": novo_nome, "email": novo_email, "senha": "WEG2026", "area": novo_area, "role": novo_papel, "ativo": True}).execute()
                            st.success("Adicionado!"); st.rerun()
                        else: st.error("O usuário já existe.")
                    else: st.warning("Preencha todos os campos obrigatórios.")

        elif aba_atual == "✏️ Editar / Desativar":
            usuario_selecionado = st.selectbox("Selecione o Usuário:", [u['login'] for u in users_db])
            if usuario_selecionado:
                user_data = next((u for u in users_db if u['login'] == usuario_selecionado), None)
                with st.form("form_edit_colab"):
                    col1, col2 = st.columns(2)
                    with col1:
                        edit_nome = st.text_input("Nome", value=user_data['nome'])
                        idx_area = areas.index(user_data['area']) if user_data['area'] in areas else 0
                        edit_area = st.selectbox("Área", areas, index=idx_area)
                    with col2:
                        roles = ["User", "Facilitador", "Admin"]
                        edit_papel = st.selectbox("Nível de Acesso", roles, index=roles.index(user_data['role']))
                        edit_ativo = st.checkbox("Colaborador Ativo", value=user_data['ativo'])
                    
                    if st.form_submit_button("Salvar Alterações"):
                        if usuario_selecionado == st.session_state['current_user']['login'] and (not edit_ativo or edit_papel != "Admin"):
                            st.error("Você não pode se desativar.")
                        else:
                            supabase.table("usuarios").update({"nome": edit_nome, "area": edit_area, "role": edit_papel, "ativo": edit_ativo}).eq("login", usuario_selecionado).execute()
                            st.success("Atualizado!"); st.rerun()
                            
                st.markdown("---")
                if st.button(f"Forçar Reset de Senha do '{usuario_selecionado}' para WEG2026", type="primary"):
                    supabase.table("usuarios").update({"senha": "WEG2026"}).eq("login", usuario_selecionado).execute()
                    st.success(f"Senha resetada!")

def pagina_administracao():
    st.header("⚙️ Administração")
    if st.session_state['current_user']['role'] != 'Admin': st.error("Acesso restrito."); return
    colA, colB = st.columns([1, 1])
    
    with colA:
        st.subheader("📍 Gestão de Locais")
        try: locais_atuais = [l['nome'] for l in supabase.table("locais").select("nome").order("nome").execute().data]
        except: locais_atuais = []
        with st.form("f_local"):
            st.write("Atuais:", ", ".join(locais_atuais) if locais_atuais else "Nenhum")
            novo_l = st.text_input("Novo Local:")
            if st.form_submit_button("Salvar") and novo_l:
                try: supabase.table("locais").insert({"nome": novo_l}).execute(); st.rerun()
                except: st.error("Este local já existe.")
        
        st.markdown("---")
        st.subheader("👨‍💼 Facilitadores")
        if locais_atuais:
            fac_map = {f['area']: f['facilitador_login'] for f in supabase.table("area_facilitadores").select("*").execute().data}
            with st.form("f_fac"):
                area_s = st.selectbox("Área", locais_atuais)
                users = supabase.table("usuarios").select("*").execute().data
                opts = ["Nenhum"] + [f"{u['nome']} ({u['login']})" for u in users if u['ativo']]
                idx = 0
                if fac_map.get(area_s):
                    for i, o in enumerate(opts):
                        if f"({fac_map.get(area_s)})" in o: idx = i; break
                novo_fac = st.selectbox("Facilitador", opts, index=idx)
                if st.form_submit_button("Salvar"):
                    if novo_fac == "Nenhum": supabase.table("area_facilitadores").delete().eq("area", area_s).execute()
                    else:
                        fac_log = novo_fac.split("(")[-1].replace(")", "")
                        supabase.table("area_facilitadores").upsert({"area": area_s, "facilitador_login": fac_log}).execute()
                    st.rerun()

    with colB:
        st.subheader("⏱️ Configuração de SLA")
        try: sla = supabase.table("sla_settings").select("*").eq("id", 1).execute().data[0]
        except: sla = {"urgente_dias": 1, "normal_dias": 3, "baixo_dias": 5}
        with st.form("f_sla"):
            c1, c2, c3 = st.columns(3)
            with c1: d_u = st.number_input("Urgente (Dias)", value=sla['urgente_dias'], min_value=1)
            with c2: d_n = st.number_input("Normal (Dias)", value=sla['normal_dias'], min_value=1)
            with c3: d_b = st.number_input("Baixo (Dias)", value=sla['baixo_dias'], min_value=1)
            if st.form_submit_button("Atualizar SLA"):
                supabase.table("sla_settings").upsert({"id": 1, "urgente_dias": d_u, "normal_dias": d_n, "baixo_dias": d_b}).execute()
                st.rerun()

        st.markdown("---")
        st.subheader("📝 Acessos Pendentes")
        reqs = supabase.table("solicitacoes").select("*").execute().data
        for req in [r for r in reqs if r['status'] == 'pendente']:
            with st.expander(f"📌 {req['nome']}", expanded=True):
                st.write(f"E-mail: {req['email']}")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("✅ Aprovar", key=f"a_{req['id']}"): aprovar_solicitacao_acesso(req['id'], req['email'], req['nome']); st.rerun()
                with c2:
                    if st.button("❌ Rejeitar", key=f"r_{req['id']}"): rejeitar_solicitacao_acesso(req['id']); st.rerun()

        st.markdown("---")
        st.subheader("📬 Disparo de Resumo Diário")
        st.write("Dispara manualmente um e-mail para todos os usuários que possuem Ações ou Tarefas pendentes no sistema hoje.")
        if st.button("Disparar E-mails de Resumo Agora", use_container_width=True, type="primary"):
            com_erro = False
            try:
                qtd_enviada = processar_resumos_diarios()
                st.success(f"✅ Disparo concluído! {qtd_enviada} usuários receberam o resumo de pendências.")
            except Exception as e:
                st.error(f"❌ Erro ao disparar: {e}")

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
