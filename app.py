
import streamlit as st
import pandas as pd
import re
import itertools
from io import BytesIO, StringIO
from fpdf import FPDF
from datetime import datetime, timedelta
import os

# --- CONFIGURAÇÃO ---
favicon_path = "logo_pdf.png" if os.path.exists("logo_pdf.png") else "📱"
st.set_page_config(page_title="SNIPER WHATSAPP", page_icon=favicon_path, layout="wide")

# --- CORES ---
COLOR_GREEN = "#25D366"  # Verde WhatsApp
COLOR_DARK = "#075E54"   # Verde Escuro WhatsApp
COLOR_BG = "#0e1117"
COLOR_TEXT = "#ecece4"

# --- CSS ---
st.markdown(f"""
<style>
    .stApp {{background-color: {COLOR_BG}; color: {COLOR_TEXT};}}
    .stButton>button {{width: 100%; background-color: {COLOR_GREEN}; color: white; border: none; border-radius: 6px; font-weight: bold; text-transform: uppercase; padding: 12px; letter-spacing: 1px;}}
    .stButton>button:hover {{background-color: {COLOR_DARK}; color: white; box-shadow: 0 2px 5px rgba(0,0,0,0.2);}}
    h1, h2, h3 {{color: {COLOR_GREEN} !important; font-family: 'Helvetica', sans-serif;}}
    .stTextInput>div>div>input, .stNumberInput>div>div>input, .stSelectbox>div>div {{background-color: #1c1f26; color: white; border: 1px solid {COLOR_GREEN};}}
    div[data-testid="stDataFrame"], .streamlit-expanderHeader {{border: 1px solid {COLOR_GREEN}; background-color: #1c1f26;}}
    div[data-testid="stFileUploader"] {{border: 1px dashed {COLOR_GREEN}; padding: 10px; border-radius: 10px;}}
</style>
""", unsafe_allow_html=True)

# --- CABEÇALHO ---
c1, c2 = st.columns([1, 5])
with c1:
    if os.path.exists("logo_app.png"): st.image("logo_app.png", width=150)
    else: st.markdown(f"# 📱", unsafe_allow_html=True)
with c2:
    st.markdown(f"<h1 style='margin-top: 15px; margin-bottom: 0px;'>SNIPER WHATSAPP</h1>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='margin-top: 0px; color: {COLOR_TEXT} !important;'>COTAS DE CONSÓRCIOS EXTRAÍDAS DE GRUPOS</h3>", unsafe_allow_html=True)
st.markdown(f"<hr style='border: 1px solid {COLOR_GREEN}; margin-top: 0;'>", unsafe_allow_html=True)

# --- FUNÇÕES ---

def limpar_moeda(texto):
    if not texto: return 0.0
    texto = str(texto).lower().strip().replace('\xa0', '').replace('&nbsp;', '')
    texto = re.sub(r'[^\d\.,]', '', texto)
    if not texto: return 0.0
    try:
        if ',' in texto and '.' in texto: return float(texto.replace('.', '').replace(',', '.'))
        elif ',' in texto: return float(texto.replace(',', '.'))
        elif '.' in texto:
             if len(texto.split('.')[1]) == 2: return float(texto)
             return float(texto.replace('.', ''))
        return float(texto)
    except: return 0.0

def converter_data(data_str):
    try: return datetime.strptime(data_str, "%d/%m/%Y")
    except ValueError:
        try: return datetime.strptime(data_str, "%d/%m/%y")
        except: return None

def processar_arquivo_whatsapp(conteudo_arquivo, nome_arquivo):
    """Lê mensagens e adiciona a ORIGEM (nome do arquivo)"""
    mensagens_validas = []
    regex_ios = r'^\[(\d{2}/\d{2}/\d{2,4}),? \d{2}:\d{2}:\d{2}\] (.*?): (.*)'
    regex_android = r'^(\d{2}/\d{2}/\d{2,4}) \d{2}:\d{2} - (.*?): (.*)'
    
    linhas = conteudo_arquivo.split('\n')
    hoje = datetime.now()
    data_corte = hoje - timedelta(days=3)
    
    buffer_msg = {"texto": "", "autor": "", "data": None, "origem": nome_arquivo}
    
    for linha in linhas:
        linha = linha.strip().replace('\u200e', '')
        if not linha: continue

        match_ios = re.search(regex_ios, linha)
        match_android = re.search(regex_android, linha)
        match = match_ios if match_ios else match_android
        
        if match:
            # Salva anterior
            if buffer_msg["texto"] and buffer_msg["data"]:
                if buffer_msg["data"] >= data_corte:
                    mensagens_validas.append(buffer_msg)
            
            # Nova msg
            data_str = match.group(1)
            autor = match.group(2)
            conteudo = match.group(3)
            data_obj = converter_data(data_str)
            
            buffer_msg = {
                "texto": conteudo,
                "autor": autor,
                "data": data_obj if data_obj else datetime(2000, 1, 1),
                "origem": nome_arquivo
            }
        else:
            buffer_msg["texto"] += "\n" + linha

    if buffer_msg["texto"] and buffer_msg["data"] and buffer_msg["data"] >= data_corte:
        mensagens_validas.append(buffer_msg)
        
    return mensagens_validas

def extrair_cotas_whatsapp(mensagens, tipo_selecionado):
    lista_cotas = []
    admins_regex = r'(?i)(bradesco|santander|itaú|itau|porto|caixa|banco do brasil|bb|rodobens|embracon|ancora|âncora|mycon|sicredi|sicoob|mapfre|hs|yamaha|zema|bancorbrás|bancorbras|servopa|disal|volkswagen|vw|unifisa|ademicon)'
    id_counter = 1

    for msg in mensagens:
        texto = msg['texto']
        autor = msg['autor']
        origem = msg['origem']
        
        if "adicionou" in texto or "removeu" in texto: continue
        
        linhas_msg = texto.split('\n')
        cota_atual = {}
        
        for linha in linhas_msg:
            linha_lower = linha.lower()
            match_admin = re.search(admins_regex, linha_lower)
            
            if match_admin:
                if cota_atual and cota_atual.get('Crédito', 0) > 0:
                     if cota_atual.get('Entrada', 0) == 0: cota_atual['Entrada'] = cota_atual['Crédito'] * 0.3
                     lista_cotas.append(cota_atual)
                     id_counter += 1
                
                cota_atual = {
                    'ID': id_counter,
                    'Admin': match_admin.group(0).upper(),
                    'Tipo': tipo_selecionado,
                    'Crédito': 0.0,
                    'Entrada': 0.0,
                    'Parcela': 0.0,
                    'Saldo': 0.0,
                    'Vendedor': autor,
                    'Origem': origem # Rastreio do arquivo
                }
                
                valores_na_linha = re.findall(r'R\$\s?([\d\.,]+)', linha)
                vals_float = sorted([limpar_moeda(v) for v in valores_na_linha], reverse=True)
                if len(vals_float) >= 1: cota_atual['Crédito'] = vals_float[0]
                if len(vals_float) >= 2: cota_atual['Entrada'] = vals_float[1]
            
            elif cota_atual:
                valores = re.findall(r'R\$\s?([\d\.,]+)', linha)
                if valores:
                    vals_float = [limpar_moeda(v) for v in valores]
                    for v in vals_float:
                        if cota_atual['Crédito'] == 0 and v > 10000:
                            cota_atual['Crédito'] = v
                        elif cota_atual['Entrada'] == 0 and v > 1000:
                            if v > cota_atual['Crédito'] * 0.05: cota_atual['Entrada'] = v
                            else: cota_atual['Parcela'] = v
                        elif cota_atual['Parcela'] == 0 and v < cota_atual['Entrada']:
                            cota_atual['Parcela'] = v

        if cota_atual and cota_atual.get('Crédito', 0) > 0:
            if cota_atual.get('Entrada', 0) == 0: cota_atual['Entrada'] = cota_atual['Crédito'] * 0.3
            lista_cotas.append(cota_atual)
            id_counter += 1

    for c in lista_cotas:
        if c['Crédito'] > 5000:
            if c['Saldo'] == 0: c['Saldo'] = (c['Crédito'] * 1.3) - c['Entrada']
            c['CustoTotal'] = c['Entrada'] + c['Saldo']
            c['EntradaPct'] = (c['Entrada']/c['Crédito']) if c['Crédito'] else 0

    return lista_cotas

def processar_combinacoes(cotas, min_cred, max_cred, max_ent, max_parc, max_custo, tipo_filtro, admin_filtro):
    combinacoes_validas = []
    cotas_por_admin = {}
    
    for cota in cotas:
        if tipo_filtro != "Todos" and cota['Tipo'] != tipo_filtro: continue
        if admin_filtro != "Todas" and cota['Admin'] != admin_filtro: continue
        adm = cota['Admin']
        if adm not in cotas_por_admin: cotas_por_admin[adm] = []
        cotas_por_admin[adm].append(cota)
    
    progress_bar = st.progress(0)
    total_admins = len(cotas_por_admin)
    current = 0

    if total_admins == 0: return pd.DataFrame()

    for admin, grupo in cotas_por_admin.items():
        if admin == "OUTROS": continue
        current += 1
        progress_bar.progress(int((current / total_admins) * 100))
        grupo.sort(key=lambda x: x['EntradaPct'])
        
        count = 0
        max_ops = 5000000 
        
        for r in range(1, 6):
            iterator = itertools.combinations(grupo, r)
            while True:
                try:
                    combo = next(iterator)
                    count += 1
                    if count > max_ops: break
                    
                    soma_ent = sum(c['Entrada'] for c in combo)
                    if soma_ent > (max_ent * 1.05): continue
                    soma_cred = sum(c['Crédito'] for c in combo)
                    if soma_cred < min_cred or soma_cred > max_cred: continue
                    soma_parc = sum(c['Parcela'] for c in combo)
                    if soma_parc > (max_parc * 1.05): continue
                    soma_custo = sum(c['CustoTotal'] for c in combo)
                    soma_saldo = sum(c['Saldo'] for c in combo)
                    custo_total_exibicao = soma_ent + soma_saldo
                    
                    prazo_medio = 0
                    if soma_parc > 0: prazo_medio = int(soma_saldo / soma_parc)

                    custo_real = (custo_total_exibicao / soma_cred) - 1
                    if custo_real > max_custo: continue
                    
                    # Dados Compostos
                    ids = " + ".join([str(c['ID']) for c in combo])
                    vendedores = list(set([c['Vendedor'] for c in combo]))
                    vendedor_str = ", ".join(vendedores)
                    origens = list(set([c['Origem'].replace('.txt','').replace('_chat','') for c in combo]))
                    origem_str = ", ".join(origens)
                    
                    detalhes = " || ".join([f"[ID {c['ID']}] R${c['Crédito']:,.0f}" for c in combo])
                    tipo_final = combo[0]['Tipo']
                    
                    status = "⚠️ PADRÃO"
                    if custo_real <= 0.20: status = "💎 OURO (<20%)"
                    elif custo_real <= 0.30: status = "🔥 IMPERDÍVEL (20-30%)"
                    elif custo_real <= 0.45: status = "✨ EXCELENTE (30-45%)"
                    elif custo_real <= 0.55: status = "✅ OPORTUNIDADE (45-55%)"
                    
                    entrada_pct = (soma_ent / soma_cred)
                    
                    combinacoes_validas.append({
                        'STATUS': status,
                        'ORIGEM': origem_str,
                        'ADMINISTRADORA': admin,
                        'CONTATO': vendedor_str,
                        'TIPO': tipo_final,
                        'IDS': ids,
                        'CRÉDITO TOTAL': soma_cred,
                        'ENTRADA TOTAL': soma_ent,
                        'ENTRADA %': entrada_pct * 100,
                        'SALDO DEVEDOR': soma_saldo,
                        'CUSTO TOTAL': custo_total_exibicao,
                        'PRAZO': prazo_medio,
                        'PARCELAS': soma_parc,
                        'CUSTO EFETIVO %': custo_real * 100,
                        'DETALHES': detalhes
                    })
                    if len([x for x in combinacoes_validas if x['ADMINISTRADORA'] == admin]) > 300: break
                except StopIteration: break
            if count > max_ops: break
    progress_bar.empty()
    return pd.DataFrame(combinacoes_validas)

# --- PDF ---
class PDF(FPDF):
    def header(self):
        self.set_fill_color(37, 211, 102)
        self.rect(0, 0, 297, 22, 'F')
        if os.path.exists("logo_pdf.png"): self.image('logo_pdf.png', 5, 3, 35)
        self.set_font('Arial', 'B', 16)
        self.set_text_color(255, 255, 255)
        self.set_xy(45, 6) 
        self.cell(0, 10, 'SNIPER WHATSAPP - RELATÓRIO DE GRUPOS', 0, 1, 'L')
        self.ln(8)

def limpar_emojis(texto):
    return texto.encode('latin-1', 'ignore').decode('latin-1').replace("?", "").strip()

def gerar_pdf_final(df):
    pdf = PDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font("Arial", size=7)
    pdf.set_fill_color(236, 236, 228)
    pdf.set_text_color(0)
    pdf.set_font("Arial", 'B', 6)
    
    # Headers - Adicionado ORIGEM
    headers = ["STS", "ORIGEM", "ADM", "CONTATO", "CREDITO", "ENTRADA", "ENT%", "SALDO", "TOTAL PAGO", "PRZ", "PARCELA", "EFET%", "DETALHES"]
    w = [22, 20, 15, 30, 20, 20, 8, 20, 20, 8, 15, 8, 70] 
    
    for i, h in enumerate(headers): pdf.cell(w[i], 8, h, 1, 0, 'C', True)
    pdf.ln()
    pdf.set_font("Arial", size=6)
    
    for index, row in df.iterrows():
        status_clean = limpar_emojis(row['STATUS'])
        pdf.cell(w[0], 8, status_clean, 1, 0, 'C')
        
        origem_clean = limpar_emojis(str(row['ORIGEM']))[:15]
        pdf.cell(w[1], 8, origem_clean, 1, 0, 'C')
        
        pdf.cell(w[2], 8, limpar_emojis(str(row['ADMINISTRADORA'])), 1, 0, 'C')
        
        contato_limpo = limpar_emojis(str(row['CONTATO']))[:22] 
        pdf.cell(w[3], 8, contato_limpo, 1, 0, 'L')
        
        pdf.cell(w[4], 8, f"R$ {row['CRÉDITO TOTAL']:,.0f}", 1, 0, 'R')
        pdf.cell(w[5], 8, f"R$ {row['ENTRADA TOTAL']:,.0f}", 1, 0, 'R')
        pdf.cell(w[6], 8, f"{row['ENTRADA %']:.0f}%", 1, 0, 'C') # 44%
        pdf.cell(w[7], 8, f"R$ {row['SALDO DEVEDOR']:,.0f}", 1, 0, 'R')
        pdf.cell(w[8], 8, f"R$ {row['CUSTO TOTAL']:,.0f}", 1, 0, 'R')
        pdf.cell(w[9], 8, str(row['PRAZO']), 1, 0, 'C')
        pdf.cell(w[10], 8, f"R$ {row['PARCELAS']:,.0f}", 1, 0, 'R')
        pdf.cell(w[11], 8, f"{row['CUSTO EFETIVO %']:.0f}%", 1, 0, 'C')
        detalhe = limpar_emojis(row['DETALHES'])
        pdf.cell(w[12], 8, detalhe[:65], 1, 1, 'L')
    return pdf.output(dest='S').encode('latin-1', 'replace')

# --- APP ---
if 'df_resultado' not in st.session_state: st.session_state.df_resultado = None
if 'mensagens_processadas' not in st.session_state: st.session_state.mensagens_processadas = []

# MUDANÇA: accept_multiple_files=True
uploaded_files = st.file_uploader("📂 ARRASTE SEUS ARQUIVOS _CHAT.TXT AQUI (Pode ser mais de um)", type=['txt'], accept_multiple_files=True)

if uploaded_files:
    todas_msgs = []
    nomes_arquivos = []
    
    for uploaded_file in uploaded_files:
        stringio = StringIO(uploaded_file.getvalue().decode("utf-8"))
        raw_text = stringio.read()
        
        # Passamos o nome do arquivo para rastreio
        msgs = processar_arquivo_whatsapp(raw_text, uploaded_file.name)
        todas_msgs.extend(msgs)
        nomes_arquivos.append(uploaded_file.name)
    
    st.session_state.mensagens_processadas = todas_msgs
    
    if todas_msgs:
        qtd = len(todas_msgs)
        st.success(f"✅ {len(uploaded_files)} Arquivos processados! {qtd} mensagens capturadas nos ÚLTIMOS 3 DIAS.")
        st.caption(f"Grupos Lidos: {', '.join(nomes_arquivos)}")
    else:
        st.warning("⚠️ Nenhuma mensagem recente encontrada nos arquivos.")

# Filtros
st.subheader("Filtros SNIPER")
col_tipo, col_admin = st.columns(2)
tipo_bem = col_tipo.selectbox("Tipo de Bem", ["Imóvel", "Automóvel", "Pesados", "Motos", "Todos"])

admins_encontradas = ["Todas"]
if st.session_state.mensagens_processadas:
    cotas_temp = extrair_cotas_whatsapp(st.session_state.mensagens_processadas, "Geral")
    admins_encontradas += sorted(list(set([c['Admin'] for c in cotas_temp])))

admin_filtro = col_admin.selectbox("Administradora", admins_encontradas)

c1, c2 = st.columns(2)
min_c = c1.number_input("Crédito Mín (R$)", 0.0, step=1000.0, value=60000.0, format="%.2f")
max_c = c1.number_input("Crédito Máx (R$)", 0.0, step=1000.0, value=710000.0, format="%.2f")
max_e = c2.number_input("Entrada Máx (R$)", 0.0, step=1000.0, value=200000.0, format="%.2f")
max_p = c2.number_input("Parcela Máx (R$)", 0.0, step=100.0, value=4500.0, format="%.2f")
max_k = st.slider("Custo Máx (%)", 0.0, 1.0, 0.55, 0.01)

if st.button("🔍 LOCALIZAR OPORTUNIDADES"):
    if st.session_state.mensagens_processadas:
        cotas = extrair_cotas_whatsapp(st.session_state.mensagens_processadas, tipo_bem)
        if cotas:
            st.session_state.df_resultado = processar_combinacoes(cotas, min_c, max_c, max_e, max_p, max_k, tipo_bem, admin_filtro)
        else:
            st.error("Nenhuma cota identificada.")
    else:
        st.error("Faça o upload dos arquivos primeiro.")

if st.session_state.df_resultado is not None:
    df_show = st.session_state.df_resultado
    if not df_show.empty:
        df_show = df_show.sort_values(by='CUSTO EFETIVO %')
        st.success(f"{len(df_show)} Oportunidades Encontradas!")
        
        st.dataframe(
            df_show,
            column_config={
                "CRÉDITO TOTAL": st.column_config.NumberColumn(format="R$ %.2f"),
                "CONTATO": st.column_config.TextColumn(width="medium"),
                "ORIGEM": st.column_config.TextColumn(width="small"),
                "ENTRADA TOTAL": st.column_config.NumberColumn(format="R$ %.2f"),
                "ENTRADA %": st.column_config.NumberColumn(format="%.2f %%"),
                "CUSTO EFETIVO %": st.column_config.NumberColumn(format="%.2f %%"),
                "STATUS": st.column_config.TextColumn(width="medium"),
            }, hide_index=True
        )
        
        c_pdf, c_xls = st.columns(2)
        try:
            pdf_bytes = gerar_pdf_final(df_show)
            c_pdf.download_button("📄 Baixar PDF (Formatado)", pdf_bytes, "Relatorio_Sniper_WPP.pdf", "application/pdf")
        except: c_pdf.error("Erro PDF")

        buf = BytesIO()
        with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
            df_ex = df_show.copy()
            # Ajuste matemático para Excel (0.44 -> 44%)
            df_ex['ENTRADA %'] = df_ex['ENTRADA %'] / 100
            df_ex['CUSTO EFETIVO %'] = df_ex['CUSTO EFETIVO %'] / 100
            
            df_ex.to_excel(writer, index=False, sheet_name='JBS_WPP')
            wb = writer.book
            ws = writer.sheets['JBS_WPP']
            
            # Formatações Excel
            header_fmt = wb.add_format({'bold': True, 'bg_color': '#25D366', 'font_color': 'white', 'border': 1})
            fmt_money = wb.add_format({'num_format': 'R$ #,##0.00'})
            fmt_perc = wb.add_format({'num_format': '0%'}) # Exibe 44% (sem casas decimais, limpo)
            
            for col_num, value in enumerate(df_ex.columns.values): ws.write(0, col_num, value, header_fmt)
            
            # Aplicando formatações nas colunas corretas (baseado na ordem do DataFrame)
            # Ordem: STATUS, ORIGEM, ADM, CONTATO, TIPO, IDS, CREDITO(6), ENTRADA(7), ENTPCT(8), SALDO(9), CUSTO(10), PRAZO, PARC(12), EFET(13)
            
            ws.set_column('G:G', 18, fmt_money) # Crédito
            ws.set_column('H:H', 18, fmt_money) # Entrada
            ws.set_column('I:I', 10, fmt_perc)  # Entrada %
            ws.set_column('J:J', 18, fmt_money) # Saldo
            ws.set_column('K:K', 18, fmt_money) # Custo Total
            ws.set_column('M:M', 18, fmt_money) # Parcela
            ws.set_column('N:N', 10, fmt_perc)  # Efetivo %
            
            ws.set_column('A:A', 25) # Status largo
            ws.set_column('B:B', 20) # Origem
            ws.set_column('D:D', 30) # Contato
            ws.set_column('O:O', 60) # Detalhes
            
        c_xls.download_button("📊 Baixar Excel (Formatado)", buf.getvalue(), "Calculo_Sniper_WPP.xlsx")
    else:
        st.warning("Nenhuma oportunidade com estes filtros.")
